#!/usr/bin/env python3
"""
xoro-epg-enricher — Xoro PVR recordings → TMDb metadata → Jellyfin NFO
Keine externen Abhängigkeiten — nur Python 3 stdlib.
"""

import argparse
import json
import os
import re
import shutil
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as _ET
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString


# ── HTTP helper ───────────────────────────────────────────────────────────────

def http_get_json(url: str, params: dict = None, timeout: int = 10) -> dict:
    if params:
        url = url + '?' + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode())


def http_get_bytes(url: str, timeout: int = 15) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.read()


def http_post(url: str, headers: dict = None, timeout: int = 10) -> int:
    req = urllib.request.Request(url, method='POST', data=b'')
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


# ── RECInfo parser ────────────────────────────────────────────────────────────

_LANG_RE    = re.compile(r'^[0-9]*(?:deu|fra|eng|ger|fre|Xfr|Xde).{0,6}$', re.I)
_GARBAGE_RE = re.compile(r'^mis.{0,4}$', re.I)


def _decode(b: bytes) -> str:
    try:
        return b.decode('utf-8').strip()
    except Exception:
        return b.decode('latin-1', errors='replace').strip()


def _is_junk(s: str) -> bool:
    if not s or len(s) < 2:
        return True
    if _LANG_RE.match(s) or _GARBAGE_RE.match(s):
        return True
    if not re.search(r'[a-zA-Z]', s):   # must contain at least one letter
        return True
    # mostly non-printable → binary noise
    printable = sum(1 for c in s if c.isprintable())
    return printable / len(s) < 0.8


def parse_recinfo(path: Path) -> dict:
    """Extract channel and title from Xoro's binary RECInfo.txt.

    Xoro stores DVB-EPG text fields with a 0x0b prefix byte followed by
    the null-terminated string. The first field is the channel name,
    the second is the programme title.
    """
    try:
        data = path.read_bytes()
    except OSError:
        return {}

    # Primary: use 0x0b DVB text-field marker
    fields = []
    for m in re.finditer(b'\x0b([^\x00]{2,})', data):
        text = _decode(m.group(1))
        if not _is_junk(text):
            fields.append(text)

    if len(fields) >= 2:
        return {'channel': fields[0], 'title': fields[1]}

    # Fallback: ASCII string scan
    strings = [s.decode('ascii', errors='replace').strip()
               for s in re.findall(b'[\x20-\x7e]{4,}', data)]
    meaningful = [s for s in strings if not _is_junk(s)]
    return {
        'channel': meaningful[0] if meaningful else '',
        'title':   meaningful[1] if len(meaningful) > 1 else '',
    }


# ── TMDb client ───────────────────────────────────────────────────────────────

class TMDb:
    BASE = 'https://api.themoviedb.org/3'
    IMG  = 'https://image.tmdb.org/t/p/w500'

    def __init__(self, api_key: str, language: str = 'de'):
        self.key  = api_key
        self.lang = language

    def _get(self, path: str, language: str = None, **params) -> dict:
        params['api_key']  = self.key
        params['language'] = language or self.lang
        return http_get_json(f'{self.BASE}{path}', params)

    def search_movie(self, title: str, year: str = None) -> list:
        params = {'query': title}
        if year:
            params['primary_release_year'] = year
        return self._get('/search/movie', **params).get('results', [])

    def search_tv(self, title: str) -> list:
        return self._get('/search/tv', query=title).get('results', [])

    def movie_details(self, tmdb_id: int) -> dict:
        d = self._get(f'/movie/{tmdb_id}')
        if not d.get('overview'):
            d['overview'] = self._get(f'/movie/{tmdb_id}', language='en').get('overview', '')
        return d

    def tv_details(self, tmdb_id: int) -> dict:
        d = self._get(f'/tv/{tmdb_id}')
        if not d.get('overview'):
            d['overview'] = self._get(f'/tv/{tmdb_id}', language='en').get('overview', '')
        return d

    def best_match(self, title: str):
        title_lower = title.lower()

        for kind, search_fn, detail_fn in [
            ('movie',  self.search_movie, self.movie_details),
            ('tvshow', self.search_tv,    self.tv_details),
        ]:
            results = search_fn(title)
            if not results:
                continue

            def score(r):
                s = 0
                name = (r.get('title') or r.get('name') or '').lower()
                if name == title_lower:       s += 50
                elif title_lower in name or name in title_lower: s += 20
                if r.get('poster_path'):      s += 10
                if r.get('overview'):         s += 10
                s += min(r.get('vote_count', 0) / 100, 20)
                return s

            best = max(results, key=score)
            return kind, detail_fn(best['id'])

        return None, None

    def best_match_movie(self, title: str, year: str = None):
        """TMDb movie search with optional year filter; retries without year on no results."""
        title_lower = title.lower()

        def score(r):
            s = 0
            name = (r.get('title') or r.get('name') or '').lower()
            if name == title_lower:                          s += 50
            elif title_lower in name or name in title_lower: s += 20
            if r.get('poster_path'):                         s += 10
            if r.get('overview'):                            s += 10
            s += min(r.get('vote_count', 0) / 100, 20)
            return s

        results = self.search_movie(title, year)
        if not results and year:
            results = self.search_movie(title)
        if not results:
            return None
        return self.movie_details(max(results, key=score)['id'])

    def poster_url(self, details: dict):
        path = details.get('poster_path')
        return f'{self.IMG}{path}' if path else None


# ── TheTVDB client ────────────────────────────────────────────────────────────

# Matches: "(S02/E09)", "(2/3)", "(2/2)", "2/3", "Teil 2"
_EPISODE_RE = re.compile(
    r'\(S(\d+)[/\s]?E(\d+)\)'           # (S02/E09)
    r'|\((\d+)/\d+\)'                    # (2/3)
    r'|\bTeil\s+(\d+)\b'                 # Teil 2
    r'|\bPart\s+(\d+)\b', re.I
)


def parse_episode_info(title: str):
    """Return (series_name, season, episode). season=1, episode=part if only part found."""
    m = _EPISODE_RE.search(title)
    if not m:
        return '', 0, 0
    series = _EPISODE_RE.sub('', title).strip(' :-–')
    if m.group(1):   # S02/E09
        return series, int(m.group(1)), int(m.group(2))
    part = int(m.group(3) or m.group(4) or m.group(5) or 1)
    return series, 1, part


# ── Folder-name parser für Scene-Releases ────────────────────────────────────

_RELEASE_TAG_RE = re.compile(
    r'\b(?:german|deutsch|english|french|dl|bluray|blu-?ray|hdtv|web-?dl|webrip|web|'
    r'bdrip|dvdrip|hdrip|hdcam|remastered|extended|directors?\.?cut|unrated|limited|'
    r'proper|rerip|repack|internal|complete|dubbed|multi|collectors?\.?edition|'
    r'2160p|1080[pi]|720[pi]|480p|4k|uhd|x264|x265|h\.?264|h\.?265|hevc|xvid|'
    r'divx|avc|flac|aac|ac3d?|dts(?:-hd)?|eac3d?|mp2|mp3)\b',
    re.I
)


def parse_folder_title(name: str):
    """Extract (title, year) from a scene-release or Jellyfin-format folder name.

    Returns ('', '') for filecrypt.cc description pages and unresolvable names.
    """
    if re.search(r'filecrypt\.cc', name, re.I):
        return '', ''

    # Jellyfin-Standardformat: "Title (Year)" or "Title (Year) {tmdb-123}"
    m = re.match(r'^(.+?)\s*\((\d{4})\)', name)
    if m:
        return m.group(1).strip(), m.group(2)

    # Dots als Trennzeichen (Release-Style mit wenig Leerzeichen)
    cleaned = name
    if cleaned.count('.') >= 2 and cleaned.count(' ') < 3:
        cleaned = cleaned.replace('.', ' ')

    # Jahr finden
    m = re.search(r'\b((?:19|20)\d{2})\b', cleaned)
    if m:
        title = cleaned[:m.start()].strip(' .-_')
        # Release-Tags aus dem Titel entfernen (z.B. "Title German DL 2004" → "Title")
        title = _RELEASE_TAG_RE.split(title)[0].strip(' .-_')
        return title, m.group(1)

    # Kein Jahr → Release-Tags abschneiden
    title = _RELEASE_TAG_RE.split(cleaned)[0].strip(' .-_')
    return (title, '') if title else ('', '')


def count_video_files(folder: Path) -> int:
    """Anzahl Video-Dateien direkt (nicht rekursiv) im Ordner."""
    try:
        return sum(
            1 for f in folder.iterdir()
            if f.is_file() and not f.name.startswith('@') and f.suffix.lower() in VIDEO_EXTS
        )
    except PermissionError:
        return 0


def has_video_file(folder: Path) -> bool:
    """True wenn der Ordner direkt (nicht rekursiv) mindestens eine Video-Datei enthält."""
    return count_video_files(folder) > 0


_SE_RE = re.compile(r'[Ss](\d+)[Ee](\d+)|(\d+)[xX][Ee](\d+)')
_SEASON_RE = re.compile(r'^(?:Season|Staffel|S)\s*0*(\d+)$', re.I)
_SKIP_DIRS = {'sample', 'subs', '@eadir'}


_ROMAN_TO_INT = {
    'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6,
    'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10, 'XI': 11, 'XII': 12,
}
_ROMAN_RE = re.compile(r'\b(XII|XI|IX|VIII|VII|VI|IV|III|II|I|X|V)\b', re.IGNORECASE)


def _parse_season_num(dirname: str):
    """Extract season number from a directory name. Supports Arabic and Roman numerals."""
    m = re.search(r'(\d+)', dirname)
    if m:
        return int(m.group(1))
    m = _ROMAN_RE.search(dirname)
    if m:
        return _ROMAN_TO_INT.get(m.group(1).upper())
    return None


def _clean_show_name(name: str) -> str:
    """Bereinigt Ordnernamen für TVDb-Suche.

    Entfernt: Unterstriche, Punkte-als-Trennzeichen (Scene-Releases), Staffelangaben,
    Jahreszahlen am Ende.
    """
    cleaned = name.replace('_', ' ')
    # Punkte als Trennzeichen ersetzen wenn kein Leerzeichen vorhanden
    # (Scene-Release-Stil: "Archie.Die.Cary.Grant.Story", "Der.Milliardaersbunker")
    if '.' in cleaned and ' ' not in cleaned:
        cleaned = cleaned.replace('.', ' ')
    cleaned = re.sub(r'\s+S\d+\s*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+(Season|Staffel)\s+\d+\s*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+(19|20)\d{2}\s*$', '', cleaned)
    return cleaned.strip()


def _nfo_plot(nfo_path: Path) -> str:
    """Liest <plot> aus einer NFO. Ignoriert führenden Non-XML-Text (Release-Notes etc.)."""
    try:
        content = nfo_path.read_text(encoding='utf-8', errors='replace')
        for marker in ('<?xml', '<episodedetails', '<tvshow', '<movie'):
            idx = content.find(marker)
            if idx >= 0:
                root = _ET.fromstring(content[idx:])
                return (root.findtext('plot') or '').strip()
    except Exception:
        pass
    return ''


def parse_se_from_filename(stem: str):
    """Return (season, episode) from stem like 'Breaking Bad S01E01' or '1xE01'. (0, 0) if not found."""
    m = _SE_RE.search(stem)
    if m:
        if m.group(1):
            return int(m.group(1)), int(m.group(2))
        return int(m.group(3)), int(m.group(4))
    return 0, 0


def extract_episode_from_number(stem: str, season_num: int) -> int:
    """Extract episode from filenames like '7p-704' where 704 = Season 7, Episode 04.
    Returns episode number (1-99), 0 if no pattern found, -1 if episode=00 (skip).
    """
    m = re.search(r'-(\d{3,4})(?:\D|$)', stem)
    if not m:
        return 0
    num = int(m.group(1))
    if num // 100 == season_num:
        ep = num % 100
        if ep == 0:
            return -1  # e.g. 7p-100: Episode 00, kein TVDb-Eintrag → überspringen
        if 1 <= ep <= 99:
            return ep
    return 0


class TVDb:
    BASE = 'https://api4.thetvdb.com/v4'

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._token  = None

    def _auth(self):
        if self._token:
            return
        req = urllib.request.Request(
            f'{self.BASE}/login',
            data=json.dumps({'apikey': self.api_key}).encode(),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            self._token = json.loads(r.read())['data']['token']

    def _get(self, path: str, **params) -> dict:
        self._auth()
        url = f'{self.BASE}{path}'
        if params:
            url += '?' + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={'Authorization': f'Bearer {self._token}'})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())

    def search_series(self, title: str) -> list:
        return self._get('/search', query=title, type='series').get('data', [])

    def series_details(self, tvdb_id: int) -> dict:
        return self._get(f'/series/{tvdb_id}/extended').get('data', {})

    def episode_overview(self, tvdb_id: int, season: int, episode: int) -> str:
        try:
            data = self._get(f'/series/{tvdb_id}/episodes/default',
                             season=season, episodeNumber=episode)
            eps = data.get('data', {}).get('episodes', [])
            if not eps:
                return ''
            ep = eps[0]
            if 'deu' in (ep.get('overviewTranslations') or []):
                try:
                    trans = self._get(f'/episodes/{ep["id"]}/translations/deu')
                    de_ov = (trans.get('data') or {}).get('overview', '')
                    if de_ov:
                        return de_ov
                except Exception:
                    pass
            return ep.get('overview', '') or ''
        except Exception:
            return ''

    def episode_info(self, tvdb_id: int, season: int, episode: int) -> dict:
        """Return {'title': ..., 'overview': ...} in DE if available, EN fallback."""
        try:
            data = self._get(f'/series/{tvdb_id}/episodes/default',
                             season=season, episodeNumber=episode)
            eps = data.get('data', {}).get('episodes', [])
            if not eps:
                return {}
            ep = eps[0]
            result = {'title': ep.get('name', '') or '', 'overview': ep.get('overview', '') or ''}
            if 'deu' in (ep.get('overviewTranslations') or []):
                try:
                    trans = self._get(f'/episodes/{ep["id"]}/translations/deu')
                    de = trans.get('data') or {}
                    if de.get('overview'):
                        result['overview'] = de['overview']
                    if de.get('name'):
                        result['title'] = de['name']
                except Exception:
                    pass
            return result
        except Exception:
            return {}

    def best_series(self, title: str):
        title_lower = title.lower()
        results = self.search_series(title)
        if not results:
            return None

        def score(r):
            name = (r.get('name') or '').lower()
            s = 0
            if name == title_lower:   s += 50
            elif title_lower in name or name in title_lower: s += 20
            if r.get('image_url'):    s += 5
            if r.get('overview'):     s += 5
            return s

        return max(results, key=score)

    def poster_url(self, series: dict):
        return series.get('image_url') or series.get('thumbnail')


# ── NFO generator ─────────────────────────────────────────────────────────────

def _text(parent, tag, text):
    el = SubElement(parent, tag)
    el.text = str(text) if text is not None else ''
    return el


def build_movie_nfo(details: dict, channel: str = '', epg_title: str = '') -> str:
    root = Element('movie')
    tmdb_title = details.get('title') or details.get('name', '')
    _text(root, 'title',         epg_title or tmdb_title)
    _text(root, 'originaltitle', details.get('original_title') or details.get('original_name', '') or tmdb_title)
    _text(root, 'plot',          details.get('overview', ''))
    _text(root, 'year',          (details.get('release_date') or details.get('first_air_date', ''))[:4])
    _text(root, 'rating',        details.get('vote_average', ''))
    _text(root, 'tmdbid',        details.get('id', ''))
    for g in details.get('genres', []):
        _text(root, 'genre', g['name'])
    if channel:
        _text(root, 'studio', channel)
    runtime = details.get('runtime') or (details.get('episode_run_time') or [None])[0]
    if runtime:
        _text(root, 'runtime', runtime)
    raw = tostring(root, encoding='unicode')
    return parseString(f'<?xml version="1.0" encoding="UTF-8"?>{raw}').toprettyxml(indent='  ', encoding=None)


def build_episode_nfo(series: dict, season: int, episode: int,
                      channel: str = '', epg_title: str = '',
                      episode_overview: str = '') -> str:
    root = Element('episodedetails')
    _text(root, 'title',       epg_title or series.get('name', ''))
    _text(root, 'showtitle',   series.get('name', ''))
    _text(root, 'season',      season)
    _text(root, 'episode',     episode)
    _text(root, 'plot',        episode_overview or epg_title or series.get('overview', ''))
    _text(root, 'year',        (series.get('firstAired') or series.get('year', ''))[:4])
    if channel:
        _text(root, 'studio', channel)
    tvdb_id = series.get('id') or series.get('tvdb_id', '')
    if tvdb_id:
        _text(root, 'uniqueid', tvdb_id)
    raw = tostring(root, encoding='unicode')
    return parseString(f'<?xml version="1.0" encoding="UTF-8"?>{raw}').toprettyxml(indent='  ', encoding=None)


def build_tvshow_nfo(series: dict) -> str:
    root = Element('tvshow')
    _text(root, 'title', series.get('name', ''))
    _text(root, 'plot', series.get('overview', ''))
    year = (series.get('firstAired') or series.get('year', ''))[:4]
    if year:
        _text(root, 'year', year)
    tvdb_id = series.get('id') or series.get('tvdb_id', '')
    if tvdb_id:
        uid = SubElement(root, 'uniqueid')
        uid.set('type', 'tvdb')
        uid.set('default', 'true')
        uid.text = str(tvdb_id)
    raw = tostring(root, encoding='unicode')
    return parseString(f'<?xml version="1.0" encoding="utf-8"?>{raw}').toprettyxml(indent='  ', encoding=None)


def build_fallback_nfo(title: str, channel: str = '') -> str:
    root = Element('movie')
    _text(root, 'title', title)
    _text(root, 'genre', 'Nicht erkannt')
    if channel:
        _text(root, 'studio', channel)
    raw = tostring(root, encoding='unicode')
    return parseString(f'<?xml version="1.0" encoding="UTF-8"?>{raw}').toprettyxml(indent='  ', encoding=None)


# ── Move helper ───────────────────────────────────────────────────────────────

def _sanitize(s: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', '', s).strip(' .')[:100]


def _nfo_info(nfo_path: Path) -> dict:
    try:
        root = _ET.parse(nfo_path).getroot()
        if root.tag == 'movie':
            # Fallback-NFO hat weder tmdbid noch plot → nicht verschieben
            recognized = bool(root.findtext('tmdbid') or root.findtext('plot'))
            return {
                'type':       'movie',
                'title':      root.findtext('title') or '',
                'year':       root.findtext('year') or '',
                'recognized': recognized,
            }
        if root.tag == 'episodedetails':
            recognized = bool(root.findtext('uniqueid') or root.findtext('plot') or root.findtext('showtitle'))
            return {
                'type':       'series',
                'showtitle':  root.findtext('showtitle') or root.findtext('title') or '',
                'title':      root.findtext('title') or '',
                'season':     (root.findtext('season') or '1').zfill(2),
                'episode':    (root.findtext('episode') or '1').zfill(2),
                'recognized': recognized,
            }
    except Exception:
        pass
    return {'type': 'unknown', 'recognized': False}


def _touch_now(path: Path):
    """Setzt mtime auf jetzt — Xoro schreibt Aufnahmedateien ohne gültigen Zeitstempel (Unix-Epoche),
    dadurch sortiert Jellyfins 'Kürzlich hinzugefügt' sie ganz ans Ende statt oben ein."""
    try:
        now = time.time()
        os.utime(path, (now, now))
    except Exception:
        pass


def move_recording(folder: Path, dest_movies: str, dest_series: str, dry_run: bool, stats: dict = None, dest_unmatched: str = None):
    nfo = folder / 'movie.nfo'
    if not nfo.exists():
        return
    info = _nfo_info(nfo)
    kind = info.get('type', 'unknown')

    if not info.get('recognized') and dest_unmatched:
        dest_base = Path(dest_unmatched)
        name = _sanitize(info.get('title') or folder.name)
        print(f'  → kein API-Match, verschiebe → Nicht erkannt')
    elif kind == 'movie' and dest_movies:
        dest_base = Path(dest_movies)
        title = _sanitize(info.get('title') or folder.name)
        year  = info.get('year', '')
        name  = f'{title} ({year})' if year else title
    elif kind == 'series' and dest_series:
        show = _sanitize(info.get('showtitle') or folder.name)
        s, e = info.get('season', '01'), info.get('episode', '01')
        ep_title = _sanitize(info.get('title', ''))
        basename = f'{show} S{s}E{e}' + (f' {ep_title}' if ep_title and ep_title != show else '')
        season_dir = Path(dest_series) / show / f'Season {s}'
        dest_ts = season_dir / f'{basename}.ts'
        if dest_ts.exists():
            print(f'  → bereits vorhanden: {dest_ts}')
            return
        if dry_run:
            print(f'  → [dry-run] würde verschieben → {season_dir}/{basename}.*')
            return
        season_dir.mkdir(parents=True, exist_ok=True)
        # Videodateien verschieben + umbenennen
        for suffix in ('', '.idx', '.meta', '.pmt'):
            src = folder / f'record.ts{suffix}'
            if src.exists():
                dest_file = season_dir / f'{basename}.ts{suffix}'
                shutil.move(str(src), str(dest_file))
                _touch_now(dest_file)
        # NFO umbenennen (movie.nfo → basename.nfo)
        nfo_src = folder / 'movie.nfo'
        if nfo_src.exists():
            shutil.move(str(nfo_src), str(season_dir / f'{basename}.nfo'))
        # Leeren Quellordner entfernen
        try:
            folder.rmdir()
        except Exception:
            pass
        print(f'  → verschoben → {season_dir}/{basename}.*')
        if stats is not None:
            stats['moved'] = stats.get('moved', 0) + 1
        return
    else:
        print(f'  → kein Zielordner für Typ "{kind}"')
        return

    if not dest_base.is_dir():
        print(f'  → Zielordner nicht gefunden: {dest_base}')
        return

    dest = dest_base / name
    if dest.exists():
        print(f'  → bereits vorhanden: {name}')
        return

    if dry_run:
        print(f'  → [dry-run] würde verschieben → {dest}')
        return

    try:
        shutil.move(str(folder), str(dest))
        for suffix in ('', '.idx', '.meta', '.pmt'):
            src = dest / f'record.ts{suffix}'
            if src.exists():
                dest_file = dest / f'{name}.ts{suffix}'
                src.rename(dest_file)
                _touch_now(dest_file)
        print(f'  → verschoben → {dest}')
        if stats is not None:
            stats['moved'] = stats.get('moved', 0) + 1
    except Exception as e:
        print(f'  → Verschieben fehlgeschlagen: {e}')


# ── Jellyfin ──────────────────────────────────────────────────────────────────

def jellyfin_refresh(url: str, api_key: str) -> bool:
    try:
        status = http_post(f'{url.rstrip("/")}/Library/Refresh', headers={'X-Emby-Token': api_key})
        return status in (200, 204)
    except Exception as e:
        print(f'  Jellyfin-Refresh fehlgeschlagen: {e}')
        return False


# ── Main ──────────────────────────────────────────────────────────────────────

def process_folder(folder: Path, tmdb, tvdb, dry_run: bool, force: bool) -> str:
    recinfo = folder / 'RECInfo.txt'
    nfo     = folder / 'movie.nfo'
    poster  = folder / 'poster.jpg'

    if not recinfo.exists():
        return 'skip:no-recinfo'
    if nfo.exists() and not force:
        return 'skip:already-done'

    info    = parse_recinfo(recinfo)
    title   = info.get('title', '').strip()
    channel = info.get('channel', '').strip()

    if not title:
        return 'skip:no-title'

    print(f'  Titel:  {title}')
    print(f'  Kanal:  {channel}')

    if dry_run:
        return 'dry-run'

    nfo_content = None
    poster_url  = None

    # Serien-Episode erkennen → TheTVDB bevorzugen
    series_name, season, episode = parse_episode_info(title)
    if series_name and tvdb:
        try:
            series = tvdb.best_series(series_name)
            if series:
                ep_ov = tvdb.episode_overview(series.get('id', 0), season, episode)
                nfo_content = build_episode_nfo(series, season, episode, channel,
                                                epg_title=title, episode_overview=ep_ov)
                poster_url  = tvdb.poster_url(series)
                print(f'  TVDb:   {series.get("name")} S{season:02d}E{episode:02d}')
            else:
                print(f'  TVDb:   kein Ergebnis für "{series_name}"')
        except Exception as e:
            print(f'  TVDb-Fehler: {e}')

    if nfo_content is None and tmdb:
        try:
            kind, details = tmdb.best_match(title)
            if details:
                nfo_content = build_movie_nfo(details, channel, epg_title=title)
                poster_url  = tmdb.poster_url(details)
                print(f'  TMDb:   {details.get("title") or details.get("name", "?")} ({kind})')
            else:
                print('  TMDb:   kein Ergebnis, Fallback-NFO')
        except Exception as e:
            print(f'  TMDb-Fehler: {e}')

    used_fallback = nfo_content is None
    if used_fallback:
        nfo_content = build_fallback_nfo(title, channel)
        print('  → kein Match, Fallback-NFO (Genre: Nicht erkannt)')

    nfo.write_text(nfo_content, encoding='utf-8')

    if poster_url and not poster.exists():
        try:
            poster.write_bytes(http_get_bytes(poster_url))
            print('  Poster: gespeichert')
        except Exception as e:
            print(f'  Poster-Fehler: {e}')

    return 'fallback' if used_fallback else 'done'


def scan_dirs(base_dirs):
    folders = []
    for base in base_dirs:
        if not base.is_dir():
            print(f'Warnung: {base} nicht gefunden', file=sys.stderr)
            continue
        for item in sorted(base.iterdir()):
            if item.is_dir() and (item / 'record.ts').exists():
                folders.append(item)
    return folders


def find_pvr_dirs() -> list:
    """Auto-detect all PVR/REC directories on mounted USB volumes."""
    import glob
    found = []
    for rec in sorted(glob.glob('/volumeUSB*/usbshare*/PVR/REC')):
        p = Path(rec)
        if p.is_dir():
            found.append(p)
    return found


VIDEO_EXTS = {'.ts', '.mkv', '.mp4', '.avi', '.m4v'}


def set_options_xml_offline(options_xml: str) -> bool:
    try:
        p = Path(options_xml)
        if not p.exists():
            print(f'  options.xml nicht gefunden: {options_xml}')
            return False
        content = p.read_text(encoding='utf-8')
        updated = content.replace(
            '<EnableInternetProviders>true</EnableInternetProviders>',
            '<EnableInternetProviders>false</EnableInternetProviders>'
        )
        if updated == content:
            print('  EnableInternetProviders bereits false oder nicht gesetzt')
            return False
        p.write_text(updated, encoding='utf-8')
        print('  EnableInternetProviders → false')
        return True
    except Exception as e:
        print(f'  Fehler: {e}')
        return False


def read_tvdb_id_from_nfo(nfo_path: Path) -> int:
    """Read TVDb ID from tvshow.nfo <uniqueid type="tvdb"> element."""
    try:
        root = _ET.parse(nfo_path).getroot()
        for uid in root.findall('uniqueid'):
            try:
                return int(uid.text)
            except (ValueError, TypeError):
                pass
    except Exception:
        pass
    return 0


def normalize_episode_nfos(dest_series: Path, tvdb, dry_run: bool) -> dict:
    """Create episode NFOs for series with non-standard filenames (no S/E pattern).

    Reads TVDb ID from tvshow.nfo, maps sorted videos in each season folder
    sequentially to TVDb episodes starting at episode 1.
    """
    if not tvdb:
        print('Fehler: --tvdb-key wird für --normalize-episodes benötigt.')
        return {'done': 0, 'skip': 0, 'error': 0}

    stats = {'done': 0, 'skip': 0, 'error': 0}

    for show_dir in sorted(dest_series.iterdir()):
        if not show_dir.is_dir() or show_dir.name.startswith('@') or show_dir.name.startswith('.'):
            continue

        tvshow_nfo = show_dir / 'tvshow.nfo'
        if not tvshow_nfo.exists():
            continue

        tvdb_id = read_tvdb_id_from_nfo(tvshow_nfo)
        if not tvdb_id:
            continue

        show_name = show_dir.name

        for season_dir in sorted(show_dir.iterdir()):
            if not season_dir.is_dir() or season_dir.name.startswith('@'):
                continue
            season_m = re.search(r'(\d+)', season_dir.name)
            if not season_m:
                continue
            season_num = int(season_m.group(1))

            to_process = []
            for video in sorted(season_dir.iterdir()):
                if video.suffix.lower() not in VIDEO_EXTS:
                    continue
                if video.with_suffix('.nfo').exists():
                    stats['skip'] += 1
                    continue
                if parse_se_from_filename(video.stem)[1]:
                    stats['skip'] += 1
                    continue
                to_process.append(video)

            if not to_process:
                continue

            print(f'\n[{show_name}] Season {season_num}: {len(to_process)} Dateien ohne NFO')

            for i, video in enumerate(to_process, start=1):
                ep_from_name = extract_episode_from_number(video.stem, season_num)
                if ep_from_name == -1:
                    print(f'  {video.name} → übersprungen (Episode 00)')
                    stats['skip'] += 1
                    continue
                ep_num = ep_from_name or i
                print(f'  {video.name} → S{season_num:02d}E{ep_num:02d}')
                try:
                    ep = tvdb.episode_info(tvdb_id, season_num, ep_num)
                    if not ep:
                        print(f'    TVDb: kein Ergebnis für S{season_num:02d}E{i:02d}')
                        stats['error'] += 1
                        continue
                    series_stub = {'id': tvdb_id, 'name': show_name}
                    nfo_content = build_episode_nfo(
                        series_stub, season_num, ep_num,
                        epg_title=ep.get('title', ''),
                        episode_overview=ep.get('overview', '')
                    )
                    nfo_path = video.with_suffix('.nfo')
                    if dry_run:
                        print(f'    [dry-run] {nfo_path.name}: {ep.get("title", "?")}')
                    else:
                        nfo_path.write_text(nfo_content, encoding='utf-8')
                        print(f'    NFO → {nfo_path.name}: {ep.get("title", "?")}')
                    stats['done'] += 1
                    time.sleep(0.3)
                except Exception as e:
                    print(f'    Fehler: {e}')
                    stats['error'] += 1

    print(f'\nNormalize-Episodes: {stats["done"]} NFOs erstellt, {stats["skip"]} übersprungen, {stats["error"]} Fehler')
    return stats


def _infer_season(ep_folders: list) -> int:
    """Infer season number from episode folder names or video filenames inside."""
    for ep_dir in ep_folders:
        m = _SE_RE.search(ep_dir.name)
        if m:
            return int(m.group(1) or m.group(3))
        for f in ep_dir.iterdir():
            if f.suffix.lower() in VIDEO_EXTS and not f.name.startswith('@'):
                m = _SE_RE.search(f.stem)
                if m:
                    return int(m.group(1) or m.group(3))
    return 0


def flatten_downloads(series_dir: Path, dry_run: bool) -> dict:
    """Flatten nested episode-folder structures so Jellyfin can scan them.

    Handles two patterns:
      A) Series/Season XX/EpisodeFolder/file.mkv   (e.g. Wednesday)
      B) Series/WrongName N/EpisodeFolder/file.mkv (e.g. Vikings, wrongly-named season folder)

    Moves video + .nfo files out of episode sub-folders into the season folder.
    Deletes Sample/ sub-folders. Renames wrongly-named season folders to "Season XX".
    @eaDir and Subs are left untouched.
    """
    if not series_dir.is_dir():
        print(f'Fehler: Pfad nicht gefunden: {series_dir}')
        return {'moved': 0, 'renamed': 0, 'skipped': 0}

    stats = {'moved': 0, 'renamed': 0, 'skipped': 0}
    MOVE_EXTS = VIDEO_EXTS | {'.nfo'}

    for show_dir in sorted(series_dir.iterdir()):
        if not show_dir.is_dir() or show_dir.name.startswith(('@', '.')):
            continue

        had_output = False

        for season_dir in sorted(show_dir.iterdir()):
            if not season_dir.is_dir() or season_dir.name.startswith(('@', '.')):
                continue
            if season_dir.name.lower() in _SKIP_DIRS:
                continue

            # Collect episode sub-folders (dirs that directly contain video files)
            ep_folders = []
            for item in sorted(season_dir.iterdir()):
                if not item.is_dir() or item.name.startswith('@') or item.name.lower() in _SKIP_DIRS:
                    continue
                if any(f.suffix.lower() in VIDEO_EXTS
                       for f in item.iterdir()
                       if not f.name.startswith('@') and not f.is_dir()):
                    ep_folders.append(item)

            if not ep_folders:
                continue

            if not had_output:
                print(f'\n[{show_dir.name}]')
                had_output = True

            # Determine target season folder
            m = _SEASON_RE.match(season_dir.name)
            if m:
                season_num = int(m.group(1))
                target_dir = season_dir
            else:
                season_num = _infer_season(ep_folders)
                if not season_num:
                    print(f'  [!] Staffelnummer nicht erkennbar: {season_dir.name}')
                    continue
                target_dir = show_dir / f'Season {season_num:02d}'
                print(f'  Ordner umbenennen: "{season_dir.name}" → "{target_dir.name}"')
                if not dry_run:
                    target_dir.mkdir(parents=True, exist_ok=True)
                stats['renamed'] += 1

            # Move files from each episode sub-folder
            for ep_dir in ep_folders:
                for f in sorted(ep_dir.iterdir()):
                    if f.is_dir() or f.name.startswith('@'):
                        continue
                    if f.suffix.lower() not in MOVE_EXTS:
                        continue
                    dest = target_dir / f.name
                    if dest.exists():
                        print(f'  [skip] {f.name}')
                        stats['skipped'] += 1
                        continue
                    if dry_run:
                        print(f'  [dry-run] {f.name} → {target_dir.name}/')
                    else:
                        shutil.move(str(f), str(dest))
                        print(f'  ✓ {f.name} → {target_dir.name}/')
                    stats['moved'] += 1

                # Delete Sample sub-folder (only previews, not needed)
                sample = ep_dir / 'Sample'
                if sample.exists() and sample.is_dir():
                    if dry_run:
                        print(f'  [dry-run] Sample/ entfernen in {ep_dir.name}')
                    else:
                        shutil.rmtree(str(sample), ignore_errors=True)

                # Remove episode folder — silently fails if @eaDir or Subs remain
                if not dry_run:
                    try:
                        ep_dir.rmdir()
                    except OSError:
                        pass

            # Remove old wrongly-named season folder if now empty
            if not dry_run and target_dir != season_dir:
                try:
                    season_dir.rmdir()
                except OSError:
                    pass

    print(f'\nFlatten: {stats["moved"]} Dateien verschoben, '
          f'{stats["renamed"]} Ordner umbenannt, {stats["skipped"]} übersprungen')
    return stats


def _process_existing_movie(folder: Path, tmdb, dry_run: bool, force: bool, stats: dict):
    """Verarbeite einen einzelnen Film-Ordner ohne RECInfo.txt."""
    nfo    = folder / 'movie.nfo'
    poster = folder / 'poster.jpg'

    if nfo.exists() and not force:
        stats['skip'] += 1
        return

    title, year = parse_folder_title(folder.name)
    if not title:
        print(f'  [{folder.name}] → übersprungen (kein Titel parsebar)')
        stats['skip'] += 1
        return

    print(f'\n[{folder.name}]')
    print(f'  Titel: {title}' + (f' ({year})' if year else ''))

    if dry_run:
        stats['skip'] += 1
        return

    nfo_content = None
    poster_url  = None

    try:
        details = tmdb.best_match_movie(title, year or None)
        if details:
            nfo_content = build_movie_nfo(details)
            poster_url  = tmdb.poster_url(details)
            matched = details.get('title') or details.get('name', '?')
            print(f'  TMDb:  {matched}')
        else:
            print('  TMDb:  kein Ergebnis, Fallback-NFO')
    except Exception as e:
        print(f'  TMDb-Fehler: {e}')

    if nfo_content is None:
        nfo_content = build_fallback_nfo(title)
        stats['fallback'] += 1
    else:
        stats['done'] += 1

    nfo.write_text(nfo_content, encoding='utf-8')

    if poster_url and not poster.exists():
        try:
            poster.write_bytes(http_get_bytes(poster_url))
            print('  Poster: gespeichert')
        except Exception as e:
            print(f'  Poster-Fehler: {e}')

    time.sleep(0.3)


def scan_existing_movies(dirs: list, tmdb, dry_run: bool, force: bool) -> dict:
    """Scanne Verzeichnisse mit bestehenden Filmen (ohne RECInfo.txt).

    Einzelfilm-Ordner werden direkt verarbeitet. Sammlungs-Ordner (kein Video
    direkt, aber Video in Unterordnern) werden eine Ebene rekursiv aufgelöst.
    """
    if not tmdb:
        print('Fehler: --tmdb-key wird für --scan-existing-movies benötigt.')
        return {'done': 0, 'skip': 0, 'error': 0, 'fallback': 0}

    stats = {'done': 0, 'skip': 0, 'error': 0, 'fallback': 0}

    for base in dirs:
        if not base.is_dir():
            print(f'Warnung: {base} nicht gefunden', file=sys.stderr)
            continue

        print(f'\n=== {base} ===')

        for folder in sorted(base.iterdir()):
            if not folder.is_dir():
                continue
            if folder.name.startswith('@') or folder.name.startswith('.'):
                continue
            if folder.name.lower() in _SKIP_DIRS:
                continue

            n_videos = count_video_files(folder)
            # Unterordner die selbst mindestens 1 Video enthalten → Sammlungsordner
            try:
                n_subdirs_with_video = sum(
                    1 for sub in folder.iterdir()
                    if sub.is_dir() and not sub.name.startswith(('@', '.'))
                    and count_video_files(sub) > 0
                )
            except PermissionError:
                n_subdirs_with_video = 0

            if n_videos == 1 and n_subdirs_with_video == 0:
                # Echter Einzelfilm-Ordner (kein Sammlungsordner)
                try:
                    _process_existing_movie(folder, tmdb, dry_run, force, stats)
                except Exception as e:
                    print(f'  Fehler: {e}')
                    stats['error'] += 1
            elif n_subdirs_with_video > 0:
                # Sammlungs-Ordner: eine Ebene rekursiv (direkte Videos im Sammlungsordner werden übersprungen)
                for sub in sorted(folder.iterdir()):
                    if not sub.is_dir() or sub.name.startswith('@') or sub.name.startswith('.'):
                        continue
                    if sub.name.lower() in _SKIP_DIRS:
                        continue
                    if count_video_files(sub) == 1:
                        try:
                            _process_existing_movie(sub, tmdb, dry_run, force, stats)
                        except Exception as e:
                            print(f'  Fehler in {sub.name}: {e}')
                            stats['error'] += 1
            # n_videos > 1 ohne Unterordner: überspringen

    print(f'\nScan-Existing-Movies: {stats["done"]} erkannt, {stats["fallback"]} Fallback, '
          f'{stats["skip"]} übersprungen, {stats["error"]} Fehler')
    return stats


def scan_existing_series(dest_series: Path, tvdb, dry_run: bool) -> dict:
    if not tvdb:
        print('Fehler: --tvdb-key wird für --scan-existing benötigt.')
        return {'done': 0, 'skip': 0, 'error': 0}

    stats = {'done': 0, 'skip': 0, 'error': 0}
    series_cache = {}

    for show_dir in sorted(dest_series.iterdir()):
        if not show_dir.is_dir() or show_dir.name.startswith('@') or show_dir.name.startswith('.'):
            continue
        show_name = show_dir.name
        search_name = _clean_show_name(show_name)

        # tvshow.nfo anlegen falls fehlend oder plot leer
        tvshow_nfo = show_dir / 'tvshow.nfo'
        if not tvshow_nfo.exists() or not _nfo_plot(tvshow_nfo):
            print(f'\n[{show_name}] tvshow.nfo fehlt')
            if search_name != show_name:
                print(f'  Suche als: "{search_name}"')
            try:
                series = tvdb.best_series(search_name)
                if series:
                    series_cache[show_name] = series
                    if dry_run:
                        print(f'  [dry-run] tvshow.nfo → {series.get("name")}')
                    else:
                        tvshow_nfo.write_text(build_tvshow_nfo(series), encoding='utf-8')
                        print(f'  tvshow.nfo → {series.get("name")}')
                    time.sleep(0.3)
                else:
                    print(f'  TVDb: kein Ergebnis für "{search_name}"')
            except Exception as e:
                print(f'  Fehler: {e}')

        # Episoden-NFOs
        for season_dir in sorted(show_dir.iterdir()):
            if not season_dir.is_dir() or season_dir.name.startswith('@'):
                continue
            folder_season = _parse_season_num(season_dir.name)
            if folder_season is None:
                continue

            for video in sorted(season_dir.iterdir()):
                if video.suffix.lower() not in VIDEO_EXTS:
                    continue
                nfo_path = video.with_suffix('.nfo')
                if nfo_path.exists() and _nfo_plot(nfo_path):
                    stats['skip'] += 1
                    continue

                file_season, ep_num = parse_se_from_filename(video.stem)
                if not ep_num:
                    print(f'  [!] Kein S/E in: {video.name}')
                    stats['skip'] += 1
                    continue
                season_num = file_season if file_season else folder_season

                print(f'\n[{show_name}] S{season_num:02d}E{ep_num:02d} – {video.name}')

                try:
                    if show_name not in series_cache:
                        series_cache[show_name] = tvdb.best_series(search_name)
                    series = series_cache.get(show_name)
                    if not series:
                        print(f'  TVDb: kein Ergebnis für "{search_name}"')
                        stats['error'] += 1
                        continue

                    ep = tvdb.episode_info(series.get('id', 0), season_num, ep_num)
                    nfo_content = build_episode_nfo(series, season_num, ep_num,
                                                   epg_title=ep.get('title', ''),
                                                   episode_overview=ep.get('overview', ''))
                    if dry_run:
                        print(f'  [dry-run] {nfo_path.name}')
                    else:
                        nfo_path.write_text(nfo_content, encoding='utf-8')
                        print(f'  NFO → {nfo_path.name}')
                    stats['done'] += 1
                    time.sleep(0.3)
                except Exception as e:
                    print(f'  Fehler: {e}')
                    stats['error'] += 1

    print(f'\nScan-Existing: {stats["done"]} NFOs erstellt, {stats["skip"]} übersprungen, {stats["error"]} Fehler')
    return stats


def main():
    parser = argparse.ArgumentParser(description='Xoro PVR Enricher')
    parser.add_argument('dirs', nargs='*')
    parser.add_argument('--tmdb-key',     default=os.environ.get('TMDB_API_KEY'))
    parser.add_argument('--tvdb-key',     default=os.environ.get('TVDB_API_KEY'))
    parser.add_argument('--jellyfin-url', default=os.environ.get('JELLYFIN_URL'))
    parser.add_argument('--jellyfin-key', default=os.environ.get('JELLYFIN_KEY'))
    parser.add_argument('--language',     default='de')
    parser.add_argument('--dry-run',      action='store_true')
    parser.add_argument('--force',        action='store_true')
    parser.add_argument('--dest-movies',    default=None, help='Zielordner für Filme nach Enrichment')
    parser.add_argument('--dest-series',    default=None, help='Zielordner für Serien nach Enrichment')
    parser.add_argument('--dest-unmatched', default=None, help='Zielordner für nicht erkannte Aufnahmen')
    parser.add_argument('--scan-existing',       action='store_true', help='Bestehende Serien-Ordner scannen, fehlende NFOs ergänzen')
    parser.add_argument('--scan-existing-movies', action='store_true', help='Bestehende Film-Ordner ohne RECInfo.txt scannen, NFOs per TMDb ergänzen')
    parser.add_argument('--normalize-episodes', action='store_true', help='Episode-NFOs für Serien mit kryptischen Dateinamen erstellen (TVDb-ID aus tvshow.nfo)')
    parser.add_argument('--flatten-downloads',  action='store_true', help='Verschachtelte Episode-Ordnerstrukturen bereinigen (z.B. nach Download)')
    parser.add_argument('--options-xml',    default='/volume1/dvb-library/jellyfin-config/root/default/Serien/options.xml',
                        help='Pfad zu Jellyfin Serien-options.xml (für AK6 Offline-Modus)')
    args = parser.parse_args()

    tmdb = TMDb(args.tmdb_key, args.language) if args.tmdb_key else None
    tvdb = TVDb(args.tvdb_key) if args.tvdb_key else None
    if not tmdb and not tvdb:
        print('Hinweis: kein API-Key → nur Fallback-NFO')

    if args.scan_existing_movies:
        if not args.dirs:
            print('Fehler: Verzeichnisse als Argumente angeben.')
            sys.exit(1)
        movie_dirs = [Path(d) for d in args.dirs]
        em_stats = scan_existing_movies(movie_dirs, tmdb, args.dry_run, args.force)
        if not args.dry_run and (em_stats['done'] > 0 or em_stats['fallback'] > 0):
            if args.jellyfin_url and args.jellyfin_key:
                print('Jellyfin-Bibliothek wird aktualisiert...')
                print('OK' if jellyfin_refresh(args.jellyfin_url, args.jellyfin_key) else 'Fehlgeschlagen')
        return

    if args.flatten_downloads:
        if not args.dest_series:
            print('Fehler: --dest-series muss für --flatten-downloads angegeben werden.')
            sys.exit(1)
        flatten_downloads(Path(args.dest_series), args.dry_run)
        return

    if args.normalize_episodes:
        if not args.dest_series:
            print('Fehler: --dest-series muss für --normalize-episodes angegeben werden.')
            sys.exit(1)
        norm_stats = normalize_episode_nfos(Path(args.dest_series), tvdb, args.dry_run)
        if not args.dry_run and norm_stats['done'] > 0 and args.jellyfin_url and args.jellyfin_key:
            print('Jellyfin-Refresh...')
            print('OK' if jellyfin_refresh(args.jellyfin_url, args.jellyfin_key) else 'Fehlgeschlagen')
        return

    if args.scan_existing:
        if not args.dest_series:
            print('Fehler: --dest-series muss für --scan-existing angegeben werden.')
            sys.exit(1)
        scan_stats = scan_existing_series(Path(args.dest_series), tvdb, args.dry_run)
        if not args.dry_run and scan_stats['done'] > 0:
            print('\nSetze Offline-Modus...')
            set_options_xml_offline(args.options_xml)
            if args.jellyfin_url and args.jellyfin_key:
                print('Jellyfin-Refresh...')
                print('OK' if jellyfin_refresh(args.jellyfin_url, args.jellyfin_key) else 'Fehlgeschlagen')
        return

    if args.dirs:
        base_dirs = [Path(d) for d in args.dirs]
    else:
        base_dirs = find_pvr_dirs()
        if not base_dirs:
            print('Kein USB-Volume mit PVR/REC gefunden.')
            return
        print(f'Auto-erkannt: {[str(d) for d in base_dirs]}')

    folders = scan_dirs(base_dirs)
    print(f'{len(folders)} Aufnahmen gefunden\n')

    stats    = {'done': 0, 'skip': 0, 'error': 0, 'fallback': 0}
    unmatched = []

    for folder in folders:
        print(f'[{folder.name}]')
        try:
            status = process_folder(folder, tmdb, tvdb, args.dry_run, args.force)
        except Exception as e:
            print(f'  Fehler: {e}')
            status = 'error'

        if status == 'done':
            stats['done'] += 1
        elif status == 'fallback':
            stats['fallback'] += 1
            unmatched.append(folder.name)
        elif status.startswith('skip') or status == 'dry-run':
            if status.startswith('skip'):
                print(f'  → {status}')
            stats['skip'] += 1
        else:
            stats['error'] += 1

        if status in ('done', 'fallback', 'skip:already-done') and (args.dest_movies or args.dest_series or args.dest_unmatched):
            move_recording(folder, args.dest_movies, args.dest_series, args.dry_run, stats, dest_unmatched=args.dest_unmatched)

        if tmdb and status in ('done', 'fallback'):
            time.sleep(0.3)

    moved    = stats.get('moved', 0)
    fallback = stats['fallback']
    print(f'\nFertig: {stats["done"]} erkannt, {fallback} nicht erkannt, {stats["skip"]} übersprungen, {stats["error"]} Fehler, {moved} verschoben')

    if unmatched and not args.dry_run:
        log_path = Path(args.dest_movies or args.dirs[0] if args.dirs else '/volume1/dvb-library') / 'unmatched.log'
        try:
            import datetime
            ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(f'\n[{ts}] {len(unmatched)} nicht erkannt:\n')
                for name in unmatched:
                    f.write(f'  - {name}\n')
            print(f'Nicht-erkannte gespeichert: {log_path}')
        except Exception as e:
            print(f'Log-Fehler: {e}')

    if args.jellyfin_url and args.jellyfin_key and not args.dry_run and (stats['done'] > 0 or fallback > 0 or moved > 0):
        print('Jellyfin-Bibliothek wird aktualisiert...')
        print('OK' if jellyfin_refresh(args.jellyfin_url, args.jellyfin_key) else 'Fehlgeschlagen')

    if not args.dry_run and (stats['done'] > 0 or fallback > 0 or moved > 0 or stats['error'] > 0):
        msg = f'{stats["done"]} erkannt, {fallback} nicht erkannt, {moved} verschoben'
        try:
            os.system(f'/usr/syno/bin/synodsmnotify admin "Xoro Enricher" "{msg}"')
        except Exception:
            pass


if __name__ == '__main__':
    main()
