#!/usr/bin/env python3
"""
migrate_sclotland.py — Migration des "Adam Dalgliesh, Sclotland Yard"-Blocks

Migriert die drei Unterordner des Sammelordners
  /volume1/1/Serien/Adam Dalgliesh, Sclotland Yard/
in saubere Jellyfin-Serienstruktur (Show/Season NN/...).

Block 1  "Mord an heiliger Stätte"  → Roy-Marsden-Dalgliesh-Serie ("A Taste for Death", 2-teilig,
                                       beide MP4s = EINE Episode → Jellyfin-Stacking -part1/-part2)
Block 2  "One Sine 1997"            → Original Sin (1997), 3 Teile = E01/E02/E03 (dieselbe Serie wie B1)
Block 3  "Mord nach Pemberley"      → Death Comes to Pemberley (BBC 2013, eigenständig)

Stil/Vorlage: migrate_series.py. Importiert TVDb/build_episode_nfo/build_tvshow_nfo/_sanitize
aus enricher.py (gleicher Ordner) via importlib (relativer Import nicht möglich).

Verwendung:
  python3 migrate_sclotland.py --tvdb-key KEY [--dry-run|--live] [--base-dir /volume1/1/Serien]

  --dry-run   ist DEFAULT (Sicherheit). Zeigt nur an, was passieren würde.
  --live      führt die Verschiebung tatsächlich aus.
  --tvdb-key  optional. Ohne Key läuft der strukturelle Dry-Run (Episodentitel werden
              übersprungen, NFOs erhalten Platzhalter).
"""

import argparse
import importlib.util
import shutil
import sys
from pathlib import Path


# ── enricher.py via importlib laden (relativer Import nicht möglich) ────────────

def _load_enricher():
    enricher_path = Path(__file__).resolve().parent / 'enricher.py'
    spec = importlib.util.spec_from_file_location('enricher', enricher_path)
    if spec is None or spec.loader is None:
        raise ImportError(f'enricher.py nicht gefunden: {enricher_path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_enr = _load_enricher()
TVDb              = _enr.TVDb
build_episode_nfo = _enr.build_episode_nfo
build_tvshow_nfo  = _enr.build_tvshow_nfo
_sanitize         = _enr._sanitize


# ── Mapping-Tabelle (vom Dry-Run zur Bestätigung sichtbar) ──────────────────────
#
# Episode-Zuordnungen sind hier explizit hinterlegt, damit Ruben sie im Dry-Run
# prüfen/korrigieren kann. Die TVDb-Serien-ID wird NICHT hartkodiert, sondern
# dynamisch über best_series(search) aufgelöst.

SAMMELORDNER = 'Adam Dalgliesh, Sclotland Yard'

# Block 1 + Block 2 gehören zur SELBEN TVDb-Serie (Roy Marsden Dalgliesh).
DALGLIESH_SEARCH = 'P.D. James Adam Dalgliesh'   # Roy Marsden, 1983–1998

# Jeder Eintrag: (source_filename_oder_None, season, episode, en_title, de_title)
# Bei mehrteiliger EINER Episode (Stacking) steht 'parts' statt 'file'.

BLOCK1 = {
    'label':        'BLOCK 1 — Mord an heiliger Stätte',
    'src_subdir':   'Mord an heiliger Stätte',
    'search':       DALGLIESH_SEARCH,
    'season':       6,
    # EINE Episode, 2 Teile → Stacking. Reihenfolge: lexikographisch kleinerer
    # Dateiname = part1, größerer = part2.
    'episodes': [
        {
            'episode':   1,
            'en_title':  'A Taste for Death',
            'de_title':  'Mord an heiliger Stätte',
            'stacked':   True,   # mehrteilige Episode → -part1/-part2, EIN NFO
        },
    ],
}

BLOCK2 = {
    'label':        'BLOCK 2 — One Sine 1997 (Original Sin)',
    'src_subdir':   'One Sine 1997',
    'search':       DALGLIESH_SEARCH,   # selbe Serie wie Block 1
    'season':       None,   # Season wird aus TVDb-Auflösung der Episode nicht benötigt;
                            # Original Sin ist eine eigene Staffel der Serie. Wir mappen
                            # die drei Teile auf E01/E02/E03 einer gemeinsamen Staffel.
    # Wort-zu-Zahl Mapping anhand Dateiname-Marker.
    'episodes': [
        {'marker': 'Part 1',       'episode': 1, 'en_title': 'Original Sin (Part 1)', 'de_title': 'Ein gewisser Gerechtigkeitssinn (Teil 1)'},
        {'marker': 'Episode Two',  'episode': 2, 'en_title': 'Original Sin (Part 2)', 'de_title': 'Ein gewisser Gerechtigkeitssinn (Teil 2)'},
        {'marker': 'Episode Three','episode': 3, 'en_title': 'Original Sin (Part 3)', 'de_title': 'Ein gewisser Gerechtigkeitssinn (Teil 3)'},
    ],
    # Original Sin ist innerhalb der Roy-Marsden-Reihe eine eigene Staffel.
    # Wir verwenden eine feste Staffelnummer, die im Dry-Run sichtbar/korrigierbar ist.
    'season_override': 11,
}

BLOCK3 = {
    'label':        'BLOCK 3 — Mord nach Pemberley (Death Comes to Pemberley)',
    'src_subdir':   'Mord nach Pemberley',
    'search':       'Death Comes to Pemberley',   # BBC 2013, eigenständig
    'show_dir':     'Death Comes to Pemberley (2013)',
    'season':       1,
    # E-Nummer wird per Regex aus dem Dateinamen extrahiert ("E01 of 2" → 1, "E02" → 2)
}

EAD_IR = '@eaDir'
IGNORE_DIRS = {EAD_IR, 'Neuer Ordner'}


# ── Helfer ──────────────────────────────────────────────────────────────────────

import re

_E_RE = re.compile(r'\bE0*(\d+)\b', re.I)


def _list_videos(folder: Path):
    """Liefert sortierte Liste von .mp4-Dateien (lexikographisch), ignoriert @eaDir & Co."""
    if not folder.is_dir():
        return []
    vids = [f for f in folder.iterdir()
            if f.is_file() and f.suffix.lower() == '.mp4' and not f.name.startswith('.')]
    return sorted(vids, key=lambda p: p.name)


def _resolve_series(tvdb, search: str, cache: dict):
    """best_series mit Cache. Gibt dict oder None zurück."""
    if not tvdb:
        return None
    if search in cache:
        return cache[search]
    try:
        series = tvdb.best_series(search)
    except Exception as e:
        print(f'  [WARN] TVDb-Suche fehlgeschlagen ({search}): {e}')
        series = None
    cache[search] = series
    return series


def _placeholder_series(name: str) -> dict:
    """Minimaler Serien-Dict für NFO-Erzeugung, wenn TVDb nichts liefert."""
    return {'name': name, 'overview': '', 'id': ''}


def _episode_meta(tvdb, series: dict, season: int, episode: int,
                  fallback_title: str, fallback_overview: str):
    """Holt {'title','overview'} von TVDb (DE bevorzugt), sonst Fallback-Platzhalter."""
    if tvdb and series and series.get('id'):
        try:
            ep = tvdb.episode_info(series.get('id', 0), season, episode)
            if ep:
                return {
                    'title':    ep.get('title') or fallback_title,
                    'overview': ep.get('overview') or fallback_overview,
                }
        except Exception as e:
            print(f'  [WARN] TVDb episode_info S{season:02d}E{episode:02d}: {e}')
    return {'title': fallback_title, 'overview': fallback_overview}


def _move(src: Path, dst: Path, dry_run: bool) -> bool:
    """Verschiebt src→dst mit Idempotenz. True bei (würde-)verschieben, False bei SKIP/Fehler."""
    if dst.exists():
        print(f'  [SKIP] bereits vorhanden: {dst.name}')
        return False
    if dry_run:
        return True
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return True
    except OSError as e:
        print(f'  [ERROR] Verschieben fehlgeschlagen ({src.name}): {e}')
        return False


def _write_nfo(path: Path, content: str, dry_run: bool):
    if path.exists():
        print(f'  [SKIP] NFO bereits vorhanden: {path.name}')
        return
    if dry_run:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
    except OSError as e:
        print(f'  [ERROR] NFO schreiben fehlgeschlagen ({path.name}): {e}')


def _write_tvshow_nfo(show_dir: Path, series: dict, dry_run: bool, *, force: bool = False):
    """Schreibt tvshow.nfo. Block 1+2: nur wenn nicht vorhanden. Block 3: immer (force)."""
    nfo = show_dir / 'tvshow.nfo'
    if nfo.exists() and not force:
        print(f'  tvshow.nfo bereits vorhanden ({show_dir.name}) → behalten')
        return
    if dry_run:
        action = 'überschreiben' if (nfo.exists() and force) else 'schreiben'
        print(f'  tvshow.nfo {action}: {show_dir.name}')
        return
    try:
        show_dir.mkdir(parents=True, exist_ok=True)
        nfo.write_text(build_tvshow_nfo(series), encoding='utf-8')
        print(f'  tvshow.nfo geschrieben: {show_dir.name}')
    except OSError as e:
        print(f'  [ERROR] tvshow.nfo ({show_dir.name}): {e}')


# ── Block 1: Mehrteilige Episode (Stacking) ─────────────────────────────────────

def process_block1(base_dir: Path, tvdb, cache: dict, dry_run: bool, stats: dict):
    cfg = BLOCK1
    print(f'\n[DRY] {cfg["label"]}' if dry_run else f'\n[LIVE] {cfg["label"]}')
    src_dir = base_dir / SAMMELORDNER / cfg['src_subdir']
    videos = _list_videos(src_dir)

    series = _resolve_series(tvdb, cfg['search'], cache)
    show_name = series.get('name') if series else cfg['search']
    show_id   = series.get('id') if series else ''
    print(f'  TVDb-Serie: {show_name} (ID: {show_id or "—"})')

    if len(videos) != 2:
        print(f'  [WARN] erwartet 2 Teile, gefunden {len(videos)} → übersprungen')
        return

    ep = cfg['episodes'][0]
    season, episode = cfg['season'], ep['episode']
    meta = _episode_meta(tvdb, series, season, episode,
                         fallback_title=ep['de_title'], fallback_overview='')
    ep_title = meta['title']
    print(f'  Staffel: {season}, Episode: {episode} — "{ep["en_title"]}" (DE: "{ep["de_title"]}")')

    show = _sanitize(show_name)
    s = str(season).zfill(2)
    e = str(episode).zfill(2)
    season_dir = base_dir / show / f'Season {s}'
    basename = f'{show} S{s}E{e}'
    ep_tit_clean = _sanitize(ep_title)
    if ep_tit_clean and ep_tit_clean != show:
        basename += f' {ep_tit_clean}'

    # part1 = lexikographisch kleinerer Dateiname, part2 = größerer
    part1, part2 = videos[0], videos[1]
    targets = [
        (part1, season_dir / f'{basename}-part1{part1.suffix}'),
        (part2, season_dir / f'{basename}-part2{part2.suffix}'),
    ]

    # tvshow.nfo (Block 1+2 gemeinsame Serie): nur wenn nicht vorhanden
    nfo_series = series if series else _placeholder_series(show_name)
    _write_tvshow_nfo(base_dir / show, nfo_series, dry_run, force=False)

    for src, dst in targets:
        ok = _move(src, dst, dry_run)
        print(f'  {src.name} → {show}/Season {s}/{dst.name}')
        if ok:
            stats['moved'] += 1

    # EIN gemeinsames NFO (ohne -part-Suffix)
    nfo_path = season_dir / f'{basename}.nfo'
    nfo_content = build_episode_nfo(nfo_series, season, episode,
                                    epg_title=ep_title,
                                    episode_overview=meta['overview'])
    print(f'  NFO: {show}/Season {s}/{nfo_path.name}')
    _write_nfo(nfo_path, nfo_content, dry_run)


# ── Block 2: Original Sin, 3 separate Episoden ──────────────────────────────────

def process_block2(base_dir: Path, tvdb, cache: dict, dry_run: bool, stats: dict):
    cfg = BLOCK2
    print(f'\n[DRY] {cfg["label"]}' if dry_run else f'\n[LIVE] {cfg["label"]}')
    src_dir = base_dir / SAMMELORDNER / cfg['src_subdir']
    videos = _list_videos(src_dir)

    series = _resolve_series(tvdb, cfg['search'], cache)
    show_name = series.get('name') if series else cfg['search']
    show_id   = series.get('id') if series else ''
    print(f'  TVDb-Serie: {show_name} (ID: {show_id or "—"})')

    season = cfg['season_override']
    show = _sanitize(show_name)
    s = str(season).zfill(2)
    season_dir = base_dir / show / f'Season {s}'

    nfo_series = series if series else _placeholder_series(show_name)
    # tvshow.nfo gemeinsame Serie: nur wenn nicht vorhanden (Block 1 hat es ggf. schon)
    _write_tvshow_nfo(base_dir / show, nfo_series, dry_run, force=False)

    for ep in cfg['episodes']:
        # passende Quelldatei über Marker finden
        match = None
        for v in videos:
            if ep['marker'].lower() in v.name.lower():
                match = v
                break
        if match is None:
            print(f'  [WARN] keine Datei für Marker "{ep["marker"]}" → übersprungen')
            continue

        episode = ep['episode']
        e = str(episode).zfill(2)
        meta = _episode_meta(tvdb, series, season, episode,
                             fallback_title=ep['de_title'], fallback_overview='')
        ep_title = meta['title']

        basename = f'{show} S{s}E{e}'
        ep_tit_clean = _sanitize(ep_title)
        if ep_tit_clean and ep_tit_clean != show:
            basename += f' {ep_tit_clean}'

        dst = season_dir / f'{basename}{match.suffix}'
        ok = _move(match, dst, dry_run)
        print(f'  Staffel: {season}, Episode: {episode} — "{ep["en_title"]}" (DE: "{ep["de_title"]}")')
        print(f'  {match.name} → {show}/Season {s}/{dst.name}')
        if ok:
            stats['moved'] += 1

        nfo_path = season_dir / f'{basename}.nfo'
        nfo_content = build_episode_nfo(nfo_series, season, episode,
                                        epg_title=ep_title,
                                        episode_overview=meta['overview'])
        print(f'  NFO: {show}/Season {s}/{nfo_path.name}')
        _write_nfo(nfo_path, nfo_content, dry_run)


# ── Block 3: Death Comes to Pemberley (eigenständig) ────────────────────────────

def process_block3(base_dir: Path, tvdb, cache: dict, dry_run: bool, stats: dict):
    cfg = BLOCK3
    print(f'\n[DRY] {cfg["label"]}' if dry_run else f'\n[LIVE] {cfg["label"]}')
    src_dir = base_dir / SAMMELORDNER / cfg['src_subdir']
    videos = _list_videos(src_dir)

    series = _resolve_series(tvdb, cfg['search'], cache)
    show_name = series.get('name') if series else cfg['search']
    show_id   = series.get('id') if series else ''
    print(f'  TVDb-Serie: {show_name} (ID: {show_id or "—"})')

    season = cfg['season']
    s = str(season).zfill(2)
    show_dir = base_dir / cfg['show_dir']      # NICHT im Sammelordner!
    season_dir = show_dir / f'Season {s}'

    nfo_series = series if series else _placeholder_series(show_name)
    # eigene tvshow.nfo: immer schreiben (force)
    _write_tvshow_nfo(show_dir, nfo_series, dry_run, force=True)

    for v in videos:
        m = _E_RE.search(v.name)
        if not m:
            print(f'  [WARN] keine E-Nummer in: {v.name} → übersprungen')
            continue
        episode = int(m.group(1))
        e = str(episode).zfill(2)

        meta = _episode_meta(tvdb, series, season, episode,
                             fallback_title='', fallback_overview='')
        ep_title = meta['title']

        # Show-Name für Dateinamen: tatsächlicher Ziel-Show-Ordnername (ohne Jahr-Klammer
        # wäre sauberer, aber wir nutzen den Serien-Namen für Konsistenz mit NFO)
        show = _sanitize(show_name)
        basename = f'{show} S{s}E{e}'
        ep_tit_clean = _sanitize(ep_title)
        if ep_tit_clean and ep_tit_clean != show:
            basename += f' {ep_tit_clean}'

        dst = season_dir / f'{basename}{v.suffix}'
        ok = _move(v, dst, dry_run)
        print(f'  Staffel: {season}, Episode: {episode}'
              + (f' — "{ep_title}"' if ep_title else ''))
        print(f'  {v.name} → {cfg["show_dir"]}/Season {s}/{dst.name}')
        if ok:
            stats['moved'] += 1

        nfo_path = season_dir / f'{basename}.nfo'
        nfo_content = build_episode_nfo(nfo_series, season, episode,
                                        epg_title=ep_title,
                                        episode_overview=meta['overview'])
        print(f'  NFO: {cfg["show_dir"]}/Season {s}/{nfo_path.name}')
        _write_nfo(nfo_path, nfo_content, dry_run)


# ── Main ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Migriert den "Adam Dalgliesh, Sclotland Yard"-Block in Jellyfin-Serienstruktur.'
    )
    parser.add_argument('--base-dir', default='/volume1/1/Serien',
                        help='Basisverzeichnis (default: /volume1/1/Serien)')
    parser.add_argument('--tvdb-key', default=None,
                        help='TVDb v4 API-Key (optional; ohne Key Platzhalter-NFOs)')
    parser.add_argument('--dry-run', action='store_true', default=True,
                        help='Nur anzeigen (DEFAULT)')
    parser.add_argument('--live', action='store_true',
                        help='Tatsächlich verschieben (hebt --dry-run auf)')
    args = parser.parse_args()

    dry_run = not args.live

    base_dir = Path(args.base_dir)
    if not base_dir.is_dir():
        print(f'[ERROR] Basisverzeichnis nicht gefunden: {base_dir}')
        sys.exit(1)

    sammel = base_dir / SAMMELORDNER
    if not sammel.is_dir():
        print(f'[ERROR] Sammelordner nicht gefunden: {sammel}')
        sys.exit(1)

    tvdb = TVDb(args.tvdb_key) if args.tvdb_key else None

    mode = 'DRY-RUN' if dry_run else 'LIVE'
    print(f'migrate_sclotland.py — Modus: {mode}')
    print(f'Basisverzeichnis: {base_dir}')
    if not tvdb:
        print('Hinweis: kein --tvdb-key → TVDb übersprungen, Platzhalter-NFOs (Mapping-Tabelle)')
    print('-' * 60)

    cache = {}
    stats = {'moved': 0}

    process_block1(base_dir, tvdb, cache, dry_run, stats)
    process_block2(base_dir, tvdb, cache, dry_run, stats)
    process_block3(base_dir, tvdb, cache, dry_run, stats)

    print('-' * 60)
    verb = 'würden verschoben' if dry_run else 'verschoben'
    print(f'Fertig: {stats["moved"]} Dateien {verb}.')
    print(f'Hinweis: Sammelordner "{SAMMELORDNER}" wird NICHT gelöscht (nur Sub-Ordner geleert).')


if __name__ == '__main__':
    main()
