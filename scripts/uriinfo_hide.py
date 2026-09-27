#!/usr/bin/env python3
"""
uriinfo_hide.py — Issue #32 / WI-3.2 Vollrollout + Rollback.

Benennt URIInfo.bin-Dateien in /volume1/1/Filme zu URIInfo.bin.xoro-hidden um
(Modus 'hide') oder zurueck (Modus 'restore'). Reines Dateisystem-Rename,
kein Loeschen, kein Jellyfin-API-Zugriff, kein Scan-Trigger.

Warum Rename statt Loeschen: Jellyfin fuehrt jede Datei mit bekannter
Video-Endung (dazu zaehlt .bin) als eigenes "Phantom"-Movie-Item. Der
Rename entzieht Jellyfin nur die Endung, die Datei bleibt vollstaendig
erhalten und ist mit 'restore' exakt rueckgaengig zu machen. Der eigentliche
Film (z.B. Die Schnecke und der Buckelwal (2020).ts) wird von diesem Skript
nie angefasst.

Feste Dateiliste: Der Scan des Dateisystems passiert genau einmal beim
Start, das Ergebnis wird sofort als JSONL geloggt, bevor eine einzige
Datei angefasst wird. Waehrend des Laufs wird nicht nachgesucht.

Idempotent: eine Datei, die im Zielzustand bereits ist (hide: .xoro-hidden
existiert bereits; restore: URIInfo.bin existiert bereits), wird
uebersprungen und als 'already_done' geloggt, nie ueberschrieben.

Beispiel:
    ./uriinfo_hide.py --mode hide --dry-run
    ./uriinfo_hide.py --mode hide
    ./uriinfo_hide.py --mode restore --dry-run
    ./uriinfo_hide.py --mode restore
"""

import argparse
import json
import os
import sys
import time

DEFAULT_SCOPE = '/volume1/1/Filme'
ORIG_NAME = 'URIInfo.bin'
HIDDEN_SUFFIX = '.xoro-hidden'


def find_candidates(scope, mode):
    """Sammelt genau einmal alle betroffenen Dateien, eine Ebene unter scope.

    hide: Ordner mit URIInfo.bin (Original vorhanden).
    restore: Ordner mit URIInfo.bin.xoro-hidden (umbenannte Datei vorhanden).
    Case-insensitive, da Xoro-Geraete den Namen nicht immer gleich schreiben.
    """
    target_name = ORIG_NAME.lower() if mode == 'hide' else (ORIG_NAME + HIDDEN_SUFFIX).lower()
    found = []
    try:
        entries = sorted(os.listdir(scope))
    except OSError as e:
        print('Scope nicht lesbar: %s (%r)' % (scope, e), file=sys.stderr)
        return found

    for entry in entries:
        folder = os.path.join(scope, entry)
        if not os.path.isdir(folder):
            continue
        try:
            names = os.listdir(folder)
        except OSError as e:
            found.append({'folder': folder, 'file': None, 'error_listing': repr(e)})
            continue
        for name in names:
            if name.lower() == target_name:
                found.append({'folder': folder, 'file': os.path.join(folder, name)})
    return found


def plan_action(item, mode):
    """Bestimmt Quelle/Ziel + ob die Datei bereits im Zielzustand ist."""
    if item.get('file') is None:
        return None, None, False  # Listing-Fehler, kein Rename moeglich

    folder = item['folder']
    src = item['file']
    if mode == 'hide':
        dst = src + HIDDEN_SUFFIX
    else:
        dst = os.path.join(folder, ORIG_NAME)

    already_done = os.path.exists(dst) and not os.path.samefile(src, dst) if os.path.exists(dst) else False
    return src, dst, already_done


def run(scope, mode, dry_run, log_path):
    candidates = find_candidates(scope, mode)
    ts = time.strftime('%Y-%m-%dT%H:%M:%S')
    counts = {'renamed': 0, 'already_done': 0, 'error': 0, 'planned': 0}

    with open(log_path, 'a', encoding='utf-8') as log:
        log.write(json.dumps({'ts': ts, 'event': 'run_start', 'mode': mode,
                               'scope': scope, 'dry_run': dry_run,
                               'candidates_found': len(candidates)},
                              ensure_ascii=False) + '\n')

        for item in candidates:
            entry = {'ts': time.strftime('%Y-%m-%dT%H:%M:%S'), 'folder': item['folder']}

            if item.get('file') is None:
                entry.update({'action': 'error', 'reason': 'listing_failed',
                              'detail': item.get('error_listing')})
                counts['error'] += 1
                log.write(json.dumps(entry, ensure_ascii=False) + '\n')
                print('FEHLER (Verzeichnis nicht lesbar): %s' % item['folder'])
                continue

            src, dst, already_done = plan_action(item, mode)
            entry['src'] = src
            entry['dst'] = dst

            if already_done:
                entry['action'] = 'already_done'
                counts['already_done'] += 1
                log.write(json.dumps(entry, ensure_ascii=False) + '\n')
                continue

            if os.path.exists(dst):
                # dst existiert, ist aber dieselbe Datei wie src (z.B. Groß-/
                # Kleinschreibung auf case-insensitive FS) -> nicht anfassen.
                entry['action'] = 'error'
                entry['reason'] = 'dst_exists_unexpected'
                counts['error'] += 1
                log.write(json.dumps(entry, ensure_ascii=False) + '\n')
                print('FEHLER (Ziel existiert bereits, unerwartet): %s' % dst)
                continue

            if dry_run:
                entry['action'] = 'planned'
                counts['planned'] += 1
                log.write(json.dumps(entry, ensure_ascii=False) + '\n')
                continue

            try:
                os.rename(src, dst)
                entry['action'] = 'renamed'
                counts['renamed'] += 1
            except OSError as e:
                entry['action'] = 'error'
                entry['reason'] = repr(e)
                counts['error'] += 1
                print('FEHLER beim Umbenennen von %s: %r' % (src, e), file=sys.stderr)

            log.write(json.dumps(entry, ensure_ascii=False) + '\n')

        summary = {'ts': time.strftime('%Y-%m-%dT%H:%M:%S'), 'event': 'run_end',
                   'mode': mode, 'dry_run': dry_run, 'counts': counts}
        log.write(json.dumps(summary, ensure_ascii=False) + '\n')

    print('')
    print('Modus: %s%s' % (mode, ' (DRY-RUN, nichts geaendert)' if dry_run else ''))
    print('Gefunden: %d' % len(candidates))
    for k in ('renamed', 'planned', 'already_done', 'error'):
        if counts[k]:
            print('  %-14s %d' % (k, counts[k]))
    print('Log: %s' % log_path)
    return 1 if counts['error'] else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--mode', choices=['hide', 'restore'], required=True,
                    help="'hide' = URIInfo.bin -> .xoro-hidden (Vollrollout). "
                         "'restore' = Rollback, macht 'hide' rueckgaengig.")
    ap.add_argument('--scope', default=DEFAULT_SCOPE,
                    help='Ordner mit den Film-Unterordnern (Standard: %s)' % DEFAULT_SCOPE)
    ap.add_argument('--dry-run', action='store_true',
                    help='Nur planen + loggen, keine Datei anfassen.')
    ap.add_argument('--log', default=None,
                    help='JSONL-Log-Pfad (Standard: uriinfo_hide_<mode>_<timestamp>.jsonl '
                         'im aktuellen Verzeichnis)')
    args = ap.parse_args()

    log_path = args.log or ('uriinfo_hide_%s_%s.jsonl' % (args.mode, time.strftime('%Y%m%d_%H%M%S')))
    return run(args.scope, args.mode, args.dry_run, log_path)


if __name__ == '__main__':
    sys.exit(main())
