#!/usr/bin/env python3
"""
Eingangsordner-Automatik (#53): Downloads aus dem Eingangsordner automatisch in die
Jellyfin-Bibliothek einsortieren (Serien; Filme nur mit --dest-movies).

  Eingang/<beliebige Struktur>/Tulsa.King.S01E01.<Titel>...mkv
    -> Serien/Tulsa King/Season 01/Tulsa King - S01E01 - <deutscher Titel>.mkv  (+ .nfo)
  Eingang/Leon.der.Profi.1994.German.DL.1080p.BluRay.x264-GRP/<Datei>.mkv
    -> Filme/Leon - Der Profi (1994)/Leon - Der Profi (1994).mkv  (+ movie.nfo, poster.jpg)
  Filme nur bei eindeutigem Treffer (Titel UND Jahr passen, genau ein Treffer); sonst bleibt alles liegen.

Standard ist Probelauf (nichts wird verändert). Echter Lauf nur mit --apply.
Nutzt TVDb/Jellyfin-Helfer aus enricher.py (muss im selben Ordner liegen). Nur Python-stdlib.
"""

import argparse
import fcntl
import json
import re
import shutil
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import enricher as E

SUB_EXTS = {'.srt', '.ass', '.sub', '.idx'}
PARTIAL_EXTS = {'.part', '.!ut', '.crdownload', '.tmp', '.rar', '.jdownloader'}
SKIP_DIRS = {'sample', 'subs', '@eadir', '_reste', '#recycle'}
MIN_VIDEO_BYTES = 100 * 1024 * 1024   # kleiner = Sample/Trailer, kein Folgen-Video

# S01E01, s01e01e02, S01E01-E02 — Staffel 1-2 stellig, Folge 1-3 stellig
_SXXEYY_RE = re.compile(r'(?<![A-Za-z0-9])[Ss](\d{1,2})[Ee](\d{1,3})((?:[-_]?[Ee]\d{1,3})*)(?!\d)(?![-_]\d)')
_YEAR_TAIL_RE = re.compile(r'\s+(?:19|20)\d{2}$')


# ── Namen lesen ───────────────────────────────────────────────────────────────

def parse_episode(name: str):
    """Aus einem Datei-/Ordnernamen (ohne Endung) -> (Serienname, Staffel, [Folgen], Token) oder None.

    'Tulsa.King.S01E03.Willkuer.GERMAN...' -> ('Tulsa King', 1, [3], 'S01E03')
    """
    m = _SXXEYY_RE.search(name)
    if not m:
        return None
    show = re.sub(r'[._]+', ' ', name[:m.start()])
    show = re.sub(r'\s+', ' ', show).strip(' -')
    show = _YEAR_TAIL_RE.sub('', show)
    eps = [int(m.group(2))] + [int(x) for x in re.findall(r'[Ee](\d{1,3})', m.group(3) or '')]
    return show, int(m.group(1)), eps, m.group(0).upper()


def year_hint(name: str):
    """Jahr VOR dem SxxExx-Teil (z. B. 'Doctor.Who.2005.S01E01' -> 2005), sonst None."""
    m = _SXXEYY_RE.search(name)
    y = re.search(r'(?<!\d)((?:19|20)\d{2})(?!\d)', name[:m.start()] if m else '')
    return int(y.group(1)) if y else None


def _names_of(r: dict):
    names = [r.get('name'), (r.get('translations') or {}).get('deu')] + list(r.get('aliases') or [])
    return [n for n in names if isinstance(n, str) and n]


def pick_series(tvdb, guess: str, year=None):
    """TVDb-Serie nur wählen, wenn eindeutig. Gibt (Serie, Grund) zurück; Serie=None bei Unsicherheit.

    Eindeutig = genau ein Treffer, dessen Name/deutscher Name/Alias dem Namen entspricht
    (ohne Satzzeichen). Mehrere Treffer (Remakes: 'Electric Dreams' 2009 vs. 2017, 'Doctor Who')
    -> Jahr aus dem Release-Namen entscheidet; fehlt es oder passt keiner -> unsicher.
    """
    results = tvdb.search_series(guess)
    g = E._norm_name(guess)

    def base(n):   # 'Electric Dreams (2017)' -> 'electricdreams'
        return E._norm_name(re.sub(r'\s*\((?:19|20)\d{2}\)\s*$', '', n))

    exact = [r for r in results if any(base(n) == g for n in _names_of(r))]
    if not exact:
        return None, 'kein Treffer mit gleichem Namen'
    if year:
        by_year = [r for r in exact if str(r.get('year', ''))[:4] == str(year)]
        if len(by_year) == 1:
            return by_year[0], ''
        return None, f'kein eindeutiger Treffer für Jahr {year}'
    if len(exact) > 1:
        return None, 'mehrere Serien mit diesem Namen (Jahr im Dateinamen fehlt)'
    # Einziger "exakter" Treffer, aber andere Treffer heißen 'Name (Jahr)' -> Remake-Gefahr
    others = [r for r in results if r is not exact[0] and any(
        base(n) == g for n in _names_of(r))]
    if others:
        return None, 'mehrere Serien mit diesem Namen'
    return exact[0], ''


def sanitize(s: str) -> str:
    """Dateisystem-sicher (SMB/Windows): keine Sonderzeichen, kein Punkt/Leerzeichen am Ende."""
    s = re.sub(r'[<>:"/\\|?*]', '', s or '')
    s = re.sub(r'\s+', ' ', s).strip(' .')
    return s[:120]


# ── Ordner/Dateien ────────────────────────────────────────────────────────────

def find_videos(inbox: Path):
    """Alle Videodateien im Eingang (rekursiv), ohne Sample/Subs/Reste."""
    for p in sorted(inbox.rglob('*')):
        if not p.is_file() or p.suffix.lower() not in E.VIDEO_EXTS:
            continue
        rel = p.relative_to(inbox)
        if any(part.lower() in SKIP_DIRS or part.startswith('@') for part in rel.parts[:-1]):
            continue
        yield p


def is_finished(p: Path, min_age: int) -> bool:
    """Noch im Entpacken/Download? Dann nicht anfassen."""
    try:
        st = p.stat()
    except OSError:
        return False
    if time.time() - st.st_mtime < min_age:
        return False
    return p.suffix.lower() not in PARTIAL_EXTS and st.st_size >= MIN_VIDEO_BYTES


def find_show_dir(series_root: Path, wanted_names):
    """Vorhandenen Serienordner finden (Vergleich ohne Satzzeichen/Groß-Klein)."""
    wanted = {E._norm_name(n) for n in wanted_names if n}
    for d in sorted(series_root.iterdir()):
        if d.is_dir() and not d.name.startswith(('@', '.', '#')) and E._norm_name(d.name) in wanted:
            return d
    return None


def tvdb_id_from_nfo(nfo: Path):
    """TVDb-ID aus tvshow.nfo; toleriert den alten Vorsatz 'series-'."""
    try:
        root = E._ET.parse(nfo).getroot()
        for uid in root.findall('uniqueid'):
            t = re.sub(r'^series-', '', (uid.text or '').strip())
            if t.isdigit():
                return int(t)
    except Exception:
        pass
    return None


# ── Jellyfin ──────────────────────────────────────────────────────────────────

def _jf(url, key, path, method='GET', body=None, timeout=20):
    req = urllib.request.Request(f'{url.rstrip("/")}{path}', method=method, headers={'X-Emby-Token': key,
                                 'Content-Type': 'application/json'}, data=json.dumps(body).encode() if body else None)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        return json.loads(raw) if raw else None


def jellyfin_refresh_series(url: str, key: str, container_path: str, name: str, wait: int = 120) -> bool:
    """Meldet Jellyfin den (neuen) Serienordner und liest genau diese Serie komplett ein (kein Voll-Scan).

    Die Meldung legt bei einer NEUEN Serie nur den Serienordner an, Staffelordner/Folgen fehlen dann noch
    (Test 2026-10-11, Tulsa King) — deshalb danach gezielter Refresh der Serie mit Recursive=true.
    """
    try:
        _jf(url, key, '/Library/Media/Updated', 'POST', {'Updates': [{'Path': container_path, 'UpdateType': 'Created'}]})
        series_id, deadline = None, time.time() + wait
        while time.time() < deadline and not series_id:
            res = _jf(url, key, '/Items?Recursive=true&IncludeItemTypes=Series&Fields=Path&SearchTerm=' +
                      urllib.parse.quote(name)) or {}
            for it in res.get('Items', []):
                if it.get('Path') == container_path:
                    series_id = it['Id']
            if not series_id:
                time.sleep(5)
        if not series_id:
            print(f'  Jellyfin kennt "{name}" noch nicht — der nächste Scan holt es nach.')
            return False
        _jf(url, key, f'/Items/{series_id}/Refresh?Recursive=true&MetadataRefreshMode=Default'
                      '&ImageRefreshMode=Default&ReplaceAllMetadata=false&ReplaceAllImages=false', 'POST')
        return True
    except Exception as e:
        print(f'  Jellyfin-Refresh fehlgeschlagen: {e}')
        return False


# ── Filme ─────────────────────────────────────────────────────────────────────

def _fold(s: str) -> str:
    """Vergleichsform für Filmtitel: Akzente entfernen (Léon = Leon), dann wie bei Serien."""
    s = unicodedata.normalize('NFKD', s or '')
    return E._norm_name(''.join(c for c in s if not unicodedata.combining(c)))


def pick_movie(tmdb, title: str, year: str):
    """TMDb-Film nur wählen, wenn eindeutig. Gibt (Film, Grund) zurück; Film=None bei Unsicherheit.

    Eindeutig = Jahr steht im Release-Namen UND genau ein Treffer mit diesem Jahr, dessen deutscher oder
    Originaltitel dem Namen entspricht (ohne Satzzeichen). Ohne Jahr oder bei mehreren Treffern: unsicher.
    """
    if not year:
        return None, 'Jahr im Dateinamen fehlt'
    g = _fold(title)
    results = tmdb.search_movie(title, year)
    exact = [r for r in results
             if str(r.get('release_date', ''))[:4] == str(year)
             and g in {_fold(r.get('title')), _fold(r.get('original_title'))}]
    if not exact:
        return None, f'kein Treffer mit gleichem Titel und Jahr {year}'
    if len(exact) > 1:
        return None, 'mehrere Filme mit diesem Titel und Jahr'
    return exact[0], ''


def process_movie(video: Path, ctx: dict, stats: dict):
    """Film aus dem Eingang einsortieren. Unsicheres bleibt liegen."""
    movies_root, tmdb = ctx.get('movies_root'), ctx.get('tmdb')
    if not movies_root:
        print(f'[?] Kein SxxExx erkannt (Film oder unklar, bleibt liegen): {video.name}')
        stats['unklar'] += 1
        return
    # Ordner mit mehreren Videos (CD1/CD2, Sammlung) nicht anfassen
    siblings = [v for v in video.parent.iterdir()
                if v.is_file() and v.suffix.lower() in E.VIDEO_EXTS and v.stat().st_size >= MIN_VIDEO_BYTES]
    if len(siblings) > 1 and video.parent != ctx['inbox']:
        print(f'[?] Mehrere Videos im Ordner (Film-Sammlung oder Teile?) — bleibt liegen: {video.name}')
        stats['unklar'] += 1
        return
    title, year = E.parse_folder_title(video.stem)
    if not year and video.parent != ctx['inbox']:
        title, year = E.parse_folder_title(video.parent.name)
    if not title:
        print(f'[?] Kein Filmtitel erkennbar — bleibt liegen: {video.name}')
        stats['unklar'] += 1
        return
    key = (E._norm_name(title), year)
    if key not in ctx['movie_cache']:
        try:
            ctx['movie_cache'][key] = pick_movie(tmdb, title, year) if tmdb else (None, 'kein TMDb-Zugang')
        except Exception as e:
            ctx['movie_cache'][key] = (None, f'TMDb-Fehler: {e}')
    movie, why = ctx['movie_cache'][key]
    if not movie:
        print(f'[?] Film "{title}" nicht sicher zuzuordnen ({why}) — bleibt liegen: {video.name}')
        stats['unklar'] += 1
        return

    name = sanitize(f"{movie.get('title') or title} ({str(movie.get('release_date', ''))[:4]})")
    dest_dir = movies_root / name
    dest = dest_dir / f'{name}{video.suffix.lower()}'
    print(f'{"[Probelauf] " if not ctx["apply"] else ""}{video.name}\n    -> Film: {dest.relative_to(movies_root)}')
    if dest_dir.exists():
        print('    [übersprungen] Zielordner existiert schon')
        stats['vorhanden'] += 1
        return
    if not ctx['apply']:
        stats['geplant'] += 1
        return

    details = tmdb.movie_details(movie['id'])
    dest_dir.mkdir(parents=True)
    shutil.move(str(video), str(dest))
    E._touch_now(dest)
    try:
        (dest_dir / 'movie.nfo').write_text(E.build_movie_nfo(details), encoding='utf-8')
        poster = tmdb.poster_url(details)
        if poster:
            (dest_dir / 'poster.jpg').write_bytes(E.http_get_bytes(poster))
        for sub in sorted(video.parent.iterdir()) if video.parent.exists() else []:
            if sub.is_file() and sub.suffix.lower() in SUB_EXTS and sub.name.startswith(video.stem):
                target = dest_dir / f'{name}{sub.name[len(video.stem):]}'
                if not target.exists():
                    shutil.move(str(sub), str(target))
    except Exception as e:
        print(f'    Warnung (Film ist einsortiert): NFO/Poster/Untertitel: {e}')

    stats['einsortiert'] += 1
    ctx['touched_movies'].add(dest_dir)
    ctx['log'].write(json.dumps({'ts': time.strftime('%Y-%m-%dT%H:%M:%S'), 'von': str(video), 'nach': str(dest),
                                 'tmdb_id': movie['id']}, ensure_ascii=False) + '\n')
    ctx['log'].flush()
    if video.parent != ctx['inbox']:
        ctx['release_dirs'].add(video.parent)


def jellyfin_notify_movie(url: str, key: str, container_path: str) -> bool:
    """Meldet Jellyfin den neuen Filmordner (kein Voll-Scan)."""
    try:
        _jf(url, key, '/Library/Media/Updated', 'POST', {'Updates': [{'Path': container_path, 'UpdateType': 'Created'}]})
        return True
    except Exception as e:
        print(f'  Jellyfin-Meldung fehlgeschlagen: {e}')
        return False


# ── Kern ──────────────────────────────────────────────────────────────────────

def process_video(video: Path, ctx: dict, stats: dict):
    stem = video.stem
    parsed = parse_episode(stem) or parse_episode(video.parent.name)
    if not parsed:
        process_movie(video, ctx, stats)
        return
    show_guess, season, eps, token = parsed
    if not show_guess:   # z. B. Dateiname nur 'S01E01.mkv' -> Ordnername probieren
        p2 = parse_episode(video.parent.name)
        show_guess = p2[0] if p2 else ''
    if not show_guess:
        print(f'[?] Serienname nicht erkennbar: {video}')
        stats['unklar'] += 1
        return

    series_root: Path = ctx['series_root']
    tvdb = ctx['tvdb']

    # Serie bestimmen (eindeutig oder gar nicht), dann Zielordner mit ID-Prüfung
    key = (E._norm_name(show_guess), year_hint(stem) or year_hint(video.parent.name))
    if key not in ctx['cache']:
        ctx['cache'][key] = pick_series(tvdb, show_guess, key[1]) if tvdb else (None, 'kein TVDb-Zugang')
    series, why = ctx['cache'][key]
    if not series:
        print(f'[?] "{show_guess}" nicht sicher zuzuordnen ({why}) — bleibt liegen: {video.name}')
        stats['unklar'] += 1
        return

    de_name, _ = E._series_de(series)
    show_name = sanitize(de_name) or sanitize(show_guess)
    tvdb_id = E._tvdb_id(series) or 0
    target_show = None
    for cand in {find_show_dir(series_root, [n]) for n in (show_guess, show_name, series.get('name'))} - {None}:
        nfo_id = tvdb_id_from_nfo(cand / 'tvshow.nfo')
        if nfo_id is None or nfo_id == tvdb_id:   # kein NFO = Name genügt; sonst muss die ID stimmen
            target_show = cand
            break
    if target_show is None:
        target_show = series_root / show_name
        if target_show.exists():   # gleichnamiger Ordner gehört zu einer anderen Serie
            print(f'[?] Ordner "{show_name}" existiert mit anderer TVDb-ID — bleibt liegen: {video.name}')
            stats['unklar'] += 1
            return

    # Folgentitel/-text auf Deutsch
    info = tvdb.episode_info(tvdb_id, season, eps[0]) if (tvdb and tvdb_id and len(eps) == 1) else {}
    ep_title = sanitize(info.get('title', ''))
    new_stem = f'{show_name} - {token}' + (f' - {ep_title}' if ep_title else '')
    season_dir = target_show / f'Season {season:02d}'
    dest = season_dir / f'{new_stem}{video.suffix.lower()}'

    print(f'{"[Probelauf] " if not ctx["apply"] else ""}{video.name}\n    -> {dest.relative_to(series_root)}'
          f'{"" if ep_title else "   (kein Folgentitel bei TVDb)"}')
    if dest.exists() or (season_dir.is_dir() and any(
            f.suffix.lower() in E.VIDEO_EXTS and f.stem == new_stem for f in season_dir.iterdir())):
        print('    [übersprungen] Ziel existiert schon')
        stats['vorhanden'] += 1
        return
    if not ctx['apply']:
        stats['geplant'] += 1
        return

    season_dir.mkdir(parents=True, exist_ok=True)
    # tvshow.nfo + Poster einmalig pro Serie
    tvshow_nfo = target_show / 'tvshow.nfo'
    if not tvshow_nfo.exists():
        tvshow_nfo.write_text(E.build_tvshow_nfo(series), encoding='utf-8')
        img = series.get('image_url') or series.get('thumbnail')
        if img and not (target_show / 'poster.jpg').exists():
            try:
                (target_show / 'poster.jpg').write_bytes(E.http_get_bytes(img))
            except Exception as e:
                print(f'    Poster nicht geladen: {e}')

    shutil.move(str(video), str(dest))
    E._touch_now(dest)
    try:
        if len(eps) == 1:
            stub = dict(series)
            stub['name'] = de_name
            nfo = E.build_episode_nfo(stub, season, eps[0], epg_title=info.get('title', ''),
                                      episode_overview=info.get('overview', ''))
            dest.with_suffix('.nfo').write_text(nfo, encoding='utf-8')
        # Untertitel mit gleichem Namensanfang mitnehmen (vorhandene nie überschreiben)
        for sub in sorted(video.parent.iterdir()) if video.parent.exists() else []:
            if sub.is_file() and sub.suffix.lower() in SUB_EXTS and sub.name.startswith(stem):
                target = season_dir / f'{new_stem}{sub.name[len(stem):]}'
                if not target.exists():
                    shutil.move(str(sub), str(target))
    except Exception as e:
        print(f'    Warnung (Video ist einsortiert): NFO/Untertitel: {e}')

    stats['einsortiert'] += 1
    ctx['touched'].add(target_show)
    ctx['log'].write(json.dumps({'ts': time.strftime('%Y-%m-%dT%H:%M:%S'), 'von': str(video), 'nach': str(dest),
                                 'tvdb_id': tvdb_id, 'staffel': season, 'folgen': eps}, ensure_ascii=False) + '\n')
    ctx['log'].flush()
    ctx['release_dirs'].add(video.parent)


JUNK_EXTS = {'.nfo', '.txt', '.sfv', '.jpg', '.jpeg', '.png', '.url', '.diz', '.md5'}
JUNK_DIRS = {'sample', 'subs'}


def _only_junk(d: Path, min_age: int) -> bool:
    """True, wenn im Ordner NUR bekannte Reste liegen (Scene-NFO, Bilder, Sample/Subs, @eaDir) und nichts frisch ist."""
    now = time.time()
    for x in d.iterdir():
        if x.name == '@eaDir':
            continue
        try:
            if now - x.stat().st_mtime < min_age:
                return False
        except OSError:
            return False
        if x.is_file() and x.suffix.lower() in JUNK_EXTS:
            continue
        if x.is_dir() and x.name.lower() in JUNK_DIRS:
            continue
        return False   # Video, Archiv, Teil-Download, unbekannte Datei/Ordner -> Ordner nicht anfassen
    return True


def _unique(path: Path) -> Path:
    n, cand = 2, path
    while cand.exists():
        cand = path.with_name(f'{path.name}_{n}')
        n += 1
    return cand


def _rmdir_if_empty(d: Path) -> bool:
    """Löscht nur einen WIRKLICH leeren Ordner (ein leeres @eaDir zählt nicht als Inhalt)."""
    try:
        eadir = d / '@eaDir'
        if eadir.is_dir() and not any(eadir.iterdir()):
            eadir.rmdir()
        d.rmdir()
        return True
    except OSError:
        return False


def cleanup_release_dirs(ctx: dict, inbox: Path):
    """Reste NICHT löschen, sondern nach _Reste verschieben — und nur aus Ordnern, in denen
    nichts Wichtiges mehr liegt (kein Video, Archiv, Teil-Download, nichts Frisches)."""
    reste = inbox / '_Reste'
    candidates = set(ctx['release_dirs'])
    # Alte Rest-Ordner früherer Läufe (nur Müll, seit > 1 h unverändert) mit aufräumen
    for d in inbox.rglob('*'):
        try:
            if (d.is_dir() and d.name != '@eaDir' and '_Reste' not in d.relative_to(inbox).parts
                    and any(x.name != '@eaDir' for x in d.iterdir()) and _only_junk(d, 3600)):
                candidates.add(d)
        except OSError:
            pass
    for d in sorted(candidates, key=lambda p: len(p.parts), reverse=True):
        try:
            if d == inbox or not d.exists() or not _only_junk(d, ctx['min_age']):
                continue
            leftovers = [x for x in d.iterdir() if x.name != '@eaDir']
            if leftovers:
                target = _unique(reste / d.name)
                target.mkdir(parents=True)
                for x in leftovers:
                    shutil.move(str(x), str(target / x.name))
            _rmdir_if_empty(d)
            # Leere Elternordner (Gruppenordner wie 'Tulsa King/') bis zum Eingang hinauf
            for parent in d.parents:
                if parent == inbox or inbox not in parent.parents:
                    break
                if not _rmdir_if_empty(parent):
                    break
        except Exception as e:
            print(f'  Aufräumen übersprungen ({d.name}): {e}')


def main():
    ap = argparse.ArgumentParser(description='Eingangsordner -> Serienbibliothek (#53)')
    ap.add_argument('--inbox', required=True, help='Eingangsordner, z. B. /volume1/1/Eingang')
    ap.add_argument('--dest-series', required=True, help='Serienbibliothek, z. B. /volume1/1/Serien')
    ap.add_argument('--tvdb-key', required=True)
    ap.add_argument('--dest-movies', help='Filmbibliothek, z. B. /volume1/1/Filme (ohne: Filme bleiben im Eingang liegen)')
    ap.add_argument('--tmdb-key', help='TMDb-Schlüssel (nötig für --dest-movies)')
    ap.add_argument('--jellyfin-movies-path-map', help='NAS-Pfad=Container-Pfad für Filme, z. B. /volume1/1/Filme=/movies')
    ap.add_argument('--apply', action='store_true', help='Wirklich ausführen (ohne: Probelauf)')
    ap.add_argument('--min-age', type=int, default=300, help='Sekunden seit letzter Änderung, bevor eine Datei als fertig gilt')
    ap.add_argument('--jellyfin-url')
    ap.add_argument('--jellyfin-key')
    ap.add_argument('--jellyfin-path-map', help='NAS-Pfad=Container-Pfad, z. B. /volume1/1/Serien=/bestehende-serien')
    ap.add_argument('--log', default='inbox_sort.jsonl')
    ap.add_argument('--lock', default='/tmp/inbox_sort.lock')
    a = ap.parse_args()

    inbox, series_root = Path(a.inbox), Path(a.dest_series)
    movies_root = Path(a.dest_movies) if a.dest_movies else None
    for p in (inbox, series_root, movies_root):
        if p is not None and not p.is_dir():
            sys.exit(f'Ordner nicht gefunden: {p}')
    if movies_root and not a.tmdb_key:
        sys.exit('--dest-movies braucht --tmdb-key')

    lock = open(a.lock, 'w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        sys.exit('Läuft bereits (Sperrdatei) — beende.')

    ctx = {'inbox': inbox, 'series_root': series_root, 'tvdb': E.TVDb(a.tvdb_key), 'cache': {}, 'apply': a.apply,
           'movies_root': movies_root, 'tmdb': E.TMDb(a.tmdb_key) if movies_root else None,
           'movie_cache': {}, 'touched_movies': set(), 'touched': set(), 'release_dirs': set(), 'min_age': a.min_age, 'log': open(a.log, 'a', encoding='utf-8')}
    stats = {'einsortiert': 0, 'geplant': 0, 'vorhanden': 0, 'unklar': 0, 'noch_nicht_fertig': 0, 'fehler': 0}

    for video in find_videos(inbox):
        if not is_finished(video, a.min_age):
            print(f'[wartet] noch nicht fertig/zu klein: {video.name}')
            stats['noch_nicht_fertig'] += 1
            continue
        try:
            process_video(video, ctx, stats)
        except Exception as e:   # eine kaputte Datei darf den Rest nicht stoppen
            print(f'[Fehler] {video.name}: {e}')
            stats['fehler'] += 1

    if a.apply:
        cleanup_release_dirs(ctx, inbox)
        if a.jellyfin_url and a.jellyfin_key and a.jellyfin_path_map and ctx['touched']:
            src, dst = a.jellyfin_path_map.split('=', 1)
            for show in sorted(ctx['touched']):
                jp = str(show).replace(src, dst, 1)
                ok = jellyfin_refresh_series(a.jellyfin_url, a.jellyfin_key, jp, show.name)
                print(f'Jellyfin informiert ({jp}): {"ok" if ok else "FEHLGESCHLAGEN"}')
    if a.apply and a.jellyfin_url and a.jellyfin_key and a.jellyfin_movies_path_map and ctx['touched_movies']:
        src, dst = a.jellyfin_movies_path_map.split('=', 1)
        for d in sorted(ctx['touched_movies']):
            jp = str(d).replace(src, dst, 1)
            ok = jellyfin_notify_movie(a.jellyfin_url, a.jellyfin_key, jp)
            print(f'Jellyfin informiert ({jp}): {"ok" if ok else "FEHLGESCHLAGEN"}')
    print('\nErgebnis:', ', '.join(f'{k}={v}' for k, v in stats.items()))


if __name__ == '__main__':
    main()
