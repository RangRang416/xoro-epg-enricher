#!/usr/bin/env python3
"""
touch_new_movie_folders.py — verhindert, dass neu hinzugefuegte Filme in
Jellyfins "Kuerzlich hinzugefuegt" fehlen.

Hintergrund: enricher.py's _touch_now() setzt die mtime nur fuer Aufnahmen,
die durch move_recording() (die Xoro-Pipeline) laufen. Manuell/extern
hinzugefuegte Filme (z.B. Scene-Release-Downloads direkt in
/volume1/1/Filme) behalten sonst das Datei-Datum der Quelle (Encode-/
Download-Datum) -> Jellyfin sortiert sie dort ein statt oben (siehe
"Das fuenfte Element"/"Leon, der Profi", 2026-09-27).

Zustandsdatei merkt sich alle schon bekannten Ordnernamen. Bei jedem Lauf:
neue Ordner (noch nicht in der Zustandsdatei) -> Video-Hauptdatei(en)
darin bekommen mtime = jetzt, Ordner wird vermerkt. Beim allerersten Lauf
auf einem Scope werden alle vorhandenen Ordner nur vermerkt (kein Touch) -
sonst wuerde der erste Lauf die komplette Bibliothek "neu datieren".

Reiner Dateisystem-Zugriff: kein Jellyfin-API-Aufruf, kein Scan-Trigger.
Gedacht als taeglicher Zusatzschritt neben dem bestehenden enricher.py-Task
(DSM-Task 3, taeglich 09:00).

Beispiel:
    ./touch_new_movie_folders.py --scope /volume1/1/Filme --dry-run
    ./touch_new_movie_folders.py --scope /volume1/1/Filme
"""

import argparse
import json
import os
import sys
import time

VIDEO_EXTS = {'.ts', '.mkv', '.mp4', '.avi', '.m4v'}
DEFAULT_SCOPE = '/volume1/1/Filme'
DEFAULT_STATE = '/volume1/dvb-library/touch_new_movie_folders_state.json'


def load_state(state_path):
    if not os.path.exists(state_path):
        return None  # Unterscheidung "Datei fehlt" (Erstlauf) von "leer" wichtig
    with open(state_path, 'r', encoding='utf-8') as fh:
        return set(json.load(fh))


def save_state(state_path, known):
    tmp = state_path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(sorted(known), fh, ensure_ascii=False, indent=2)
    os.replace(tmp, state_path)  # atomar, kein halbgeschriebener State bei Absturz


def video_files_in(folder):
    try:
        names = os.listdir(folder)
    except OSError:
        return []
    return [os.path.join(folder, n) for n in names
            if os.path.splitext(n)[1].lower() in VIDEO_EXTS]


def run(scope, state_path, dry_run):
    try:
        entries = sorted(e for e in os.listdir(scope)
                         if os.path.isdir(os.path.join(scope, e)))
    except OSError as e:
        print('Scope nicht lesbar: %s (%r)' % (scope, e), file=sys.stderr)
        return 2

    known = load_state(state_path)
    first_run = known is None
    if first_run:
        known = set()
        print('Erstlauf fuer diesen Scope: alle %d vorhandenen Ordner werden nur '
              'vermerkt, nicht angefasst.' % len(entries))

    new_folders = [] if first_run else [e for e in entries if e not in known]
    touched, no_video = [], []

    for name in new_folders:
        folder = os.path.join(scope, name)
        videos = video_files_in(folder)
        if not videos:
            no_video.append(name)
            continue
        if not dry_run:
            now = time.time()
            for v in videos:
                try:
                    os.utime(v, (now, now))
                except OSError as e:
                    print('FEHLER beim Touch von %s: %r' % (v, e), file=sys.stderr)
                    continue
        touched.append(name)

    if not dry_run:
        save_state(state_path, known | set(entries))

    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    print('touch_new_movie_folders  %s%s' % (ts, ' (DRY-RUN)' if dry_run else ''))
    print('Scope: %s' % scope)
    print('Bekannte Ordner vorher: %d, gesamt jetzt: %d' % (len(known), len(entries)))
    if first_run:
        print('Neu getoucht: 0 (Erstlauf, nur Zustand angelegt)')
    else:
        print('Neu erkannt: %d, davon getoucht: %d' % (len(new_folders), len(touched)))
        if touched:
            for n in touched:
                print('  + %s' % n)
        if no_video:
            print('Ohne Videodatei (nicht getoucht, aber vermerkt): %d' % len(no_video))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--scope', default=DEFAULT_SCOPE)
    ap.add_argument('--state', default=DEFAULT_STATE)
    ap.add_argument('--dry-run', action='store_true',
                    help='Nur anzeigen, Zustandsdatei nicht schreiben, keine Datei anfassen.')
    args = ap.parse_args()
    return run(args.scope, args.state, args.dry_run)


if __name__ == '__main__':
    sys.exit(main())
