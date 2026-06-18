#!/usr/bin/env python3
"""
migrate_series.py — WI-3 Migrations-Skript

Migriert Enricher-Flat-Folder (Typ A) in Jellyfin-kompatible Serienstruktur.
Typ-B-Ordner (bereits organisiert) werden automatisch übersprungen.

Verwendung:
  python3 migrate_series.py [--dry-run] [--base-dir /volume1/1/Serien]
"""

import argparse
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path


def _sanitize(s: str) -> str:
    """Gleiche Logik wie enricher.py."""
    return re.sub(r'[<>:"/\\|?*]', '', s).strip(' .')[:100]


def _parse_nfo(nfo_path: Path):
    """
    Liest movie.nfo und gibt (showtitle, season, episode, title) zurück.
    Gibt None zurück wenn das Root-Tag kein <episodedetails> ist.
    """
    try:
        tree = ET.parse(nfo_path)
    except ET.ParseError as e:
        raise ValueError(f"XML-Parse-Fehler in {nfo_path}: {e}")

    root = tree.getroot()
    if root.tag != 'episodedetails':
        return None

    def _text(tag):
        el = root.find(tag)
        return el.text.strip() if el is not None and el.text else ''

    showtitle = _text('showtitle')
    season_raw = _text('season')
    episode_raw = _text('episode')
    title = _text('title')

    if not showtitle or not season_raw or not episode_raw:
        raise ValueError(f"Pflichtfelder fehlen in {nfo_path} (showtitle/season/episode)")

    try:
        season = int(season_raw)
        episode = int(episode_raw)
    except ValueError:
        raise ValueError(f"season/episode sind keine Ganzzahlen in {nfo_path}")

    return showtitle, season, episode, title


def _is_type_a(folder: Path) -> bool:
    """
    Typ A: Ordner hat movie.nfo mit <episodedetails> als Root-Tag.
    Ordner mit Season-Unterordnern oder ohne movie.nfo → Typ B, überspringen.
    """
    # Schnell-Check: Season-Unterordner vorhanden?
    for child in folder.iterdir():
        if child.is_dir() and re.match(r'^Season\s+\d+$', child.name, re.IGNORECASE):
            return False

    nfo = folder / 'movie.nfo'
    if not nfo.exists():
        return False

    try:
        result = _parse_nfo(nfo)
        return result is not None
    except (ValueError, Exception):
        return False


def _compute_basename(showtitle: str, season: int, episode: int, title: str):
    """
    Gibt (show, season_str, basename) zurück.
    """
    show = _sanitize(showtitle)
    s = str(season).zfill(2)
    e = str(episode).zfill(2)

    ep_title = ''
    if title and title != showtitle:
        ep_title = _sanitize(title)

    basename = f'{show} S{s}E{e}'
    if ep_title:
        basename += f' {ep_title}'

    return show, s, basename


def _find_source_files(folder: Path) -> dict:
    """
    Sucht alle zu verschiebenden Dateien im Quellordner.
    Gibt ein Dict zurück: Erweiterung → Pfad
    Relevante Erweiterungen: .ts, .ts.idx, .ts.meta, .ts.pmt, movie.nfo
    """
    files = {}

    for f in folder.iterdir():
        if not f.is_file():
            continue
        name = f.name

        if name == 'movie.nfo':
            files['nfo'] = f
        elif name.endswith('.ts.idx'):
            files['ts.idx'] = f
        elif name.endswith('.ts.meta'):
            files['ts.meta'] = f
        elif name.endswith('.ts.pmt'):
            files['ts.pmt'] = f
        elif name.endswith('.ts'):
            files['ts'] = f
        # poster.jpg, RECInfo.txt, URIInfo.bin, @eaDir → ignorieren

    return files


def migrate(base_dir: Path, dry_run: bool):
    """
    Hauptlogik. Gibt (moved, skipped, errors) zurück.
    """
    moved = 0
    skipped = 0
    errors = 0

    # Nur Depth-1-Ordner
    try:
        entries = sorted(base_dir.iterdir())
    except PermissionError as e:
        print(f"[ERROR] Kann {base_dir} nicht lesen: {e}")
        return 0, 0, 1

    for folder in entries:
        if not folder.is_dir():
            continue

        # Typ-B-Ordner überspringen
        if not _is_type_a(folder):
            print(f"[SKIP ] {folder.name} — kein Typ-A-Ordner (Typ B oder kein movie.nfo)")
            skipped += 1
            continue

        # NFO parsen
        nfo_path = folder / 'movie.nfo'
        try:
            parsed = _parse_nfo(nfo_path)
        except ValueError as e:
            print(f"[ERROR] {folder.name} — {e}")
            errors += 1
            continue

        if parsed is None:
            print(f"[SKIP ] {folder.name} — movie.nfo hat kein <episodedetails>-Root")
            skipped += 1
            continue

        showtitle, season, episode, title = parsed

        try:
            show, s, basename = _compute_basename(showtitle, season, episode, title)
        except Exception as e:
            print(f"[ERROR] {folder.name} — Basename-Berechnung fehlgeschlagen: {e}")
            errors += 1
            continue

        target_dir = base_dir / show / f'Season {s}'
        ts_target = target_dir / f'{basename}.ts'

        # Idempotenz-Check
        if ts_target.exists():
            print(f"[SKIP ] {folder.name} — bereits vorhanden: {ts_target}")
            skipped += 1
            continue

        # Quelldateien finden
        source_files = _find_source_files(folder)

        if 'ts' not in source_files:
            print(f"[SKIP ] {folder.name} — keine .ts-Datei gefunden")
            skipped += 1
            continue

        # Ziel-Mapping aufbauen
        ext_map = {
            'ts':     (source_files.get('ts'),      f'{basename}.ts'),
            'ts.idx': (source_files.get('ts.idx'),  f'{basename}.ts.idx'),
            'ts.meta':(source_files.get('ts.meta'), f'{basename}.ts.meta'),
            'ts.pmt': (source_files.get('ts.pmt'),  f'{basename}.ts.pmt'),
            'nfo':    (source_files.get('nfo'),      f'{basename}.nfo'),
        }

        if dry_run:
            print(f"[DRY  ] {folder.name}")
            print(f"         → Zielordner: {target_dir}")
            for ext, (src, dst_name) in ext_map.items():
                if src:
                    print(f"         → {src.name}  →  {dst_name}")
            moved += 1
            continue

        # Zielordner anlegen
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"[ERROR] {folder.name} — Zielordner konnte nicht erstellt werden: {e}")
            errors += 1
            continue

        # Dateien verschieben
        move_ok = True
        moved_files = []
        for ext, (src, dst_name) in ext_map.items():
            if src is None:
                continue
            dst = target_dir / dst_name
            try:
                shutil.move(str(src), str(dst))
                moved_files.append((src, dst))
            except OSError as e:
                print(f"[ERROR] {folder.name} — Verschieben fehlgeschlagen ({src.name}): {e}")
                move_ok = False
                errors += 1
                break

        if not move_ok:
            # Teilweise verschobene Dateien NICHT zurückrollen — manuell prüfen
            print(f"[ERROR] {folder.name} — Teilverschub, Quellordner NICHT gelöscht")
            continue

        print(f"[MOVE ] {folder} → {target_dir / basename}.*")

        # Quellordner entfernen (inkl. Reste: poster.jpg etc.)
        try:
            shutil.rmtree(folder)
        except OSError as e:
            print(f"[WARN ] {folder.name} — Ordner konnte nicht gelöscht werden: {e}")

        moved += 1

    return moved, skipped, errors


def main():
    parser = argparse.ArgumentParser(
        description='Migriert Enricher-Flat-Folder (Typ A) in Jellyfin-Serienstruktur.'
    )
    parser.add_argument(
        '--base-dir',
        default='/volume1/1/Serien',
        help='Basisverzeichnis mit den Serienordnern (default: /volume1/1/Serien)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Nur anzeigen was passieren würde, nichts verschieben'
    )
    args = parser.parse_args()

    base_dir = Path(args.base_dir)
    if not base_dir.exists():
        print(f"[ERROR] Basisverzeichnis existiert nicht: {base_dir}")
        raise SystemExit(1)
    if not base_dir.is_dir():
        print(f"[ERROR] Basisverzeichnis ist kein Verzeichnis: {base_dir}")
        raise SystemExit(1)

    mode = 'DRY-RUN' if args.dry_run else 'LIVE'
    print(f"migrate_series.py — Modus: {mode}")
    print(f"Basisverzeichnis: {base_dir}")
    print('-' * 60)

    moved, skipped, errors = migrate(base_dir, args.dry_run)

    print('-' * 60)
    verb = 'würden verschoben' if args.dry_run else 'verschoben'
    print(f"Fertig: {moved} {verb}, {skipped} übersprungen, {errors} Fehler")

    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
