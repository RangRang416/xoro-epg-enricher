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

    def search_movie(self, title: str) -> list:
        return self._get('/search/movie', query=title).get('results', [])

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
                      channel: str = '', epg_title: str = '') -> str:
    root = Element('episodedetails')
    _text(root, 'title',       epg_title or series.get('name', ''))
    _text(root, 'showtitle',   series.get('name', ''))
    _text(root, 'season',      season)
    _text(root, 'episode',     episode)
    _text(root, 'plot',        series.get('overview', ''))
    _text(root, 'year',        (series.get('firstAired') or series.get('year', ''))[:4])
    if channel:
        _text(root, 'studio', channel)
    tvdb_id = series.get('id') or series.get('tvdb_id', '')
    if tvdb_id:
        _text(root, 'uniqueid', tvdb_id)
    raw = tostring(root, encoding='unicode')
    return parseString(f'<?xml version="1.0" encoding="UTF-8"?>{raw}').toprettyxml(indent='  ', encoding=None)


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
        dest_base = Path(dest_series)
        show  = _sanitize(info.get('showtitle') or folder.name)
        s, e  = info.get('season', '01'), info.get('episode', '01')
        ep    = _sanitize(info.get('title', ''))
        name  = f'{show} - S{s}E{e}' + (f' {ep}' if ep and ep != show else '')
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
                src.rename(dest / f'{name}.ts{suffix}')
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
                nfo_content = build_episode_nfo(series, season, episode, channel, epg_title=title)
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
    args = parser.parse_args()

    tmdb = TMDb(args.tmdb_key, args.language) if args.tmdb_key else None
    tvdb = TVDb(args.tvdb_key) if args.tvdb_key else None
    if not tmdb and not tvdb:
        print('Hinweis: kein API-Key → nur Fallback-NFO')

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
