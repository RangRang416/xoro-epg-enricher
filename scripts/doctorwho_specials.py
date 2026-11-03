#!/usr/bin/env python3
"""
Doctor-Who-Specials aus dem Eingang einsortieren (#56).

Die Release-Ordner heißen 'Doctor.Who.2005.S04S01.Der.andere.Doktor...' (S04S01 = Special 1 nach Staffel 4).
TheTVDB führt diese Folgen in Staffel 0 (Specials) mit eigener Nummerierung; die Automatik (inbox.py) kann das
nicht aus dem Namen ableiten. Deshalb steht die Zuordnung hier fest (geprüft am 2026-11-03 gegen TVDb, Serie 78804).

Ziel: Serien/Doctor Who (2005)/Season 00/Doctor Who (2005) - S00E<nn> - <deutscher Titel>.mkv + .nfo

Läuft auf der NAS (Python 3.8, nur stdlib). Ohne --apply nur Probelauf. Verschiebt innerhalb desselben
Volumes (sofort, keine Kopie), überschreibt nie, löscht nichts.
Schlüssel kommen aus inbox_run.sh (werden nie ausgegeben).

  ssh synology 'cd /volume1/dvb-library && python3 -' < scripts/doctorwho_specials.py            # Probelauf
  ssh synology 'cd /volume1/dvb-library && python3 - --apply' < scripts/doctorwho_specials.py    # ausführen
  (zusätzlich --refresh: Jellyfin liest nur die Serie Doctor Who neu ein, kein Bibliotheks-Scan)
"""
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, '/volume1/dvb-library')
import enricher as E  # noqa: E402
import inbox  # noqa: E402

TVDB_SERIES = 78804
SHOW = 'Doctor Who (2005)'
INBOX = Path('/volume1/1/Eingang')
SERIES_ROOT = Path('/volume1/1/Serien')
# Präfix des Release-Ordners -> TVDb-Special-Nummer (Staffel 0)
MAPPING = {
    'S04S01': 9,    # The Next Doctor (Der andere Doktor)
    'S04S02': 13,   # Planet of the Dead (Planet der Toten)
    'S04S03': 14,   # The Waters of Mars (Der rote Garten)
    'S04S04': 16,   # The End of Time (1)
    'S04S05': 17,   # The End of Time (2)
}


def main(apply: bool, refresh: bool):
    sh = Path('/volume1/dvb-library/inbox_run.sh').read_text()
    tvdb = E.TVDb(re.search(r'--tvdb-key\s+(\S+)', sh).group(1))
    target = SERIES_ROOT / SHOW / 'Season 00'
    series = {'name': SHOW.replace(' (2005)', ''), 'firstAired': '2005-03-26'}
    moved = 0
    for token, num in MAPPING.items():
        cands = [v for v in INBOX.rglob('*.mkv')
                 if f'.{token}.' in v.name and '/@eaDir/' not in str(v) and '/Sample/' not in str(v)]
        if len(cands) != 1:
            print(f'{token}: {len(cands)} Treffer im Eingang — übersprungen')
            continue
        video = cands[0]
        info = tvdb.episode_info(TVDB_SERIES, 0, num)
        title = inbox.sanitize(info.get('title', ''))
        if not title:
            print(f'{token}: kein Titel bei TVDb (S00E{num:02d}) — übersprungen')
            continue
        dest = target / f'{SHOW} - S00E{num:02d} - {title}{video.suffix.lower()}'
        print(f'{"" if apply else "[Probelauf] "}{token} {video.stat().st_size // 2**20} MB\n    -> {dest.relative_to(SERIES_ROOT)}')
        if dest.exists():
            print('    [übersprungen] Ziel existiert schon')
            continue
        if not apply:
            continue
        target.mkdir(parents=True, exist_ok=True)
        shutil.move(str(video), str(dest))
        E._touch_now(dest)
        nfo = E.build_episode_nfo(series, 0, num, epg_title=info.get('title', ''),
                                  episode_overview=info.get('overview', ''))
        dest.with_suffix('.nfo').write_text(nfo, encoding='utf-8')
        moved += 1
    print(f'{moved} Specials einsortiert' if apply else 'Probelauf beendet, nichts verändert')
    if apply and refresh and moved:
        key = re.search(r'--jellyfin-key\s+(\S+)', sh).group(1)
        ok = inbox.jellyfin_refresh_series('http://192.168.2.9:8096', key, f'/bestehende-serien/{SHOW}', SHOW)
        print('Jellyfin-Refresh der Serie:', 'ok' if ok else 'fehlgeschlagen')


main('--apply' in sys.argv, '--refresh' in sys.argv)
