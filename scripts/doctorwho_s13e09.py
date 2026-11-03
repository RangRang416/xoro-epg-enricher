#!/usr/bin/env python3
"""
Doctor Who S13E09 (Die Macht des Doktors): die UK-Filmfassung (eine Datei) ist die Folge in Jellyfin; Teil 1 und
Teil 2 (zwei Dateien derselben Folge) kommen unverändert nach Eingang/_Reste/DoctorWho-S13E09-Teile (#56).

Läuft auf der NAS (Python 3.8, nur stdlib), Probelauf ohne --apply. Nur Moves im selben Volume, nichts gelöscht,
nichts überschrieben. Schlüssel aus inbox_run.sh (nie ausgegeben).

  ssh synology 'cd /volume1/dvb-library && python3 -' < scripts/doctorwho_s13e09.py             # Probelauf
  ssh synology 'cd /volume1/dvb-library && python3 - --apply' < scripts/doctorwho_s13e09.py     # ausführen
"""
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, '/volume1/dvb-library')
import enricher as E  # noqa: E402

PACK = Path('/volume1/1/Eingang/Doctor Who 2005 S01 - S13 Complete German DL 720p BluRay x264-MIX')
SEASON = Path('/volume1/1/Serien/Doctor Who (2005)/Season 13')
KEEP = Path('/volume1/1/Eingang/_Reste/DoctorWho-S13E09-Teile')
STEM = 'Doctor Who (2005) - S13E09'


def main(apply: bool):
    film = PACK / 'Doctor.Who.2005.S13E09.UK-Filmfassung.German.DL.720p.BluRay.x264-WDC/wdc-doctorwho.2005.s13e09.ukfilmfassung-720p.mkv'
    teil2 = PACK / 'Doctor.Who.2005.S13E09.Teil.2.German.DL.720p.BluRay.x264-WDC/wdc-doctorwho.2005.s13e09.teil2-720p.mkv'
    teil1 = SEASON / f'{STEM}.mkv'
    for p in (film, teil2, teil1):
        if not p.is_file():
            print('Fehlt, Abbruch:', p)
            return
    sh = Path('/volume1/dvb-library/inbox_run.sh').read_text()
    info = E.TVDb(re.search(r'--tvdb-key\s+(\S+)', sh).group(1)).episode_info(78804, 13, 9)
    print('TVDb S13E09:', info.get('title') or '(kein Titel)')
    plan = [(teil1, KEEP / 'Teil1.mkv'), (teil1.with_suffix('.nfo'), KEEP / 'Teil1.nfo'),
            (teil2, KEEP / 'Teil2.mkv'), (film, SEASON / f'{STEM}.mkv')]
    for a, b in plan:
        print(('' if apply else '[Probelauf] ') + f'{a.name}  ->  {b}')
    if not apply:
        return
    KEEP.mkdir(parents=True, exist_ok=True)
    # erst Teil 1 aus Serien herausnehmen (macht den Zielnamen frei), dann Filmfassung hinein
    for a, b in plan:
        if b.exists():
            print('Ziel existiert schon, Abbruch:', b)
            return
        shutil.move(str(a), str(b))
    E._touch_now(SEASON / f'{STEM}.mkv')
    # TVDb führt für S13E09 keinen Titel (Stand 2026-11-03); sonst hieße die Folge wie die Serie -> deutscher Filmtitel von Hand
    title = info.get('title', '') or 'Die Macht des Doktors'
    nfo = E.build_episode_nfo({'name': 'Doctor Who', 'firstAired': '2005-03-26'}, 13, 9, epg_title=title,
                              episode_overview=info.get('overview', ''))
    (SEASON / f'{STEM}.nfo').write_text(nfo, encoding='utf-8')
    print('fertig')


main('--apply' in sys.argv)
