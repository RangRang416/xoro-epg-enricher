#!/usr/bin/env python3
"""
Doctor Who: Bestandsfolgen ohne eigenen Titel bzw. mit verschobener Nummer richtig einordnen (#56).

Die Release-Gruppen haben Weihnachts- und Jubiläumsfolgen als 'SxxE00' o. ä. in die Staffeln gelegt; TVDb führt sie in
Staffel 0 (Specials). Weil es in der Staffel keine passende Nummer gibt, bekam die NFO den Serientitel und (bei E00)
den Text von Folge 1. Zuordnung unten ist aus den ursprünglichen Release-Namen (inbox_sort.jsonl), den Laufzeiten
und den TVDb-Daten abgeleitet (2026-11-03) und steht fest.

  alt (Serien/Doctor Who (2005)/Season NN/...)  ->  neu (Season 00 bzw. Season 07), Titel/Text deutsch von TVDb.
Alle Dateien mit demselben Namensanfang (.mkv, .nfo, Untertitel) ziehen um; die NFO wird neu geschrieben.
Läuft auf der NAS (Python 3.8, nur stdlib), Probelauf ohne --apply. Nur Moves im selben Volume, nichts gelöscht,
nichts überschrieben (bei vorhandenem Ziel: übersprungen). Schlüssel aus inbox_run.sh (nie ausgegeben).

  ssh synology 'cd /volume1/dvb-library && python3 -' < scripts/doctorwho_bestand_specials.py            # Probelauf
  ssh synology 'cd /volume1/dvb-library && python3 - --apply' < scripts/doctorwho_bestand_specials.py    # ausführen
Die Zuordnung (alt -> neu) wird in Serien/Doctor Who (2005)/_zuordnung_2026-11-03.txt festgehalten (Rückweg von Hand).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, '/volume1/dvb-library')
import enricher as E  # noqa: E402
import inbox  # noqa: E402

TVDB_SERIES = 78804
SHOW = 'Doctor Who (2005)'
ROOT = Path('/volume1/1/Serien') / SHOW
# (alte Staffel, alte Folge) -> (neue Staffel, neue Folge)
MAPPING = [
    # Weihnachts-/Jubiläumsfolgen -> Staffel 0 (TVDb-Nummern; Namen gegen die Release-Ordner geprüft)
    ((2, 0), (0, 2)),      # Die Weihnachtsinvasion       (The Christmas Invasion)
    ((3, 0), (0, 4)),      # The Runaway Bride
    ((4, 0), (0, 7)),      # Voyage of the Damned
    ((6, 0), (0, 34)),     # Fest der Liebe               (A Christmas Carol)
    ((7, 0), (0, 48)),     # Sternenhimmel                (The Doctor, the Widow and the Wardrobe)
    ((8, 13), (0, 142)),   # Hereingeschneit              (Last Christmas)
    ((9, 13), (0, 148)),   # Besuch bei River Song        (The Husbands of River Song)
    ((10, 0), (0, 149)),   # The Return of Doctor Mysterio
    ((10, 13), (0, 154)),  # Twice Upon a Time
    ((11, 11), (0, 156)),  # Tödlicher Fund               (Resolution)
    ((12, 11), (0, 157)),  # Revolution of the Daleks
    ((13, 7), (0, 158)),   # Eve of the Daleks
    ((13, 8), (0, 159)),   # Legend of the Sea Devils
    ((7, 15), (0, 83)),    # Der Tag des Doktors          (The Day of the Doctor)
    ((7, 16), (0, 84)),    # Die Zeit des Doktors         (The Time of the Doctor)
    # Staffel 7: Die Release-Gruppe (RSG) zählt "Die Schneemänner" als E06; ab da liegt alles eine Nummer zu hoch
    # (Datei E06 = 59 min = Schneemänner, trug aber den Titel "Die Glocken von Saint John" usw.). Reihenfolge wichtig.
    ((7, 6), (0, 66)),     # Die Schneemänner             (The Snowmen)
    ((7, 7), (7, 6)),      # Die Glocken von Saint John
    ((7, 8), (7, 7)),      # Die Ringe von Akhaten
    ((7, 9), (7, 8)),      # Kalter Krieg
    ((7, 10), (7, 9)),     # Hide (Geisterjagd)
    ((7, 11), (7, 10)),    # Das Herz der TARDIS
    ((7, 12), (7, 11)),    # Der feuerrote Schrecken
    ((7, 13), (7, 12)),    # Albtraum in Silber
    ((7, 14), (7, 13)),    # Der Name des Doktors
]


def main(apply: bool):
    sh = Path('/volume1/dvb-library/inbox_run.sh').read_text()
    tvdb = E.TVDb(re.search(r'--tvdb-key\s+(\S+)', sh).group(1))
    series = {'name': SHOW.replace(' (2005)', ''), 'firstAired': '2005-03-26'}
    log, done, vacated = [], 0, set()
    for (os_, oe), (ns, ne) in MAPPING:
        old_dir = ROOT / f'Season {os_:02d}'
        old_stem = f'{SHOW} - S{os_:02d}E{oe:02d}'
        files = [f for f in old_dir.iterdir() if f.is_file() and (f.stem == old_stem or f.name.startswith((old_stem + '.', old_stem + ' - ')))]
        video = [f for f in files if f.suffix.lower() in E.VIDEO_EXTS]
        if len(video) != 1:
            print(f'S{os_:02d}E{oe:02d}: {len(video)} Videos gefunden — übersprungen')
            continue
        info = tvdb.episode_info(TVDB_SERIES, ns, ne)
        title = inbox.sanitize(info.get('title', ''))
        if not title:
            print(f'S{os_:02d}E{oe:02d} -> S{ns:02d}E{ne:02d}: kein Titel bei TVDb — übersprungen')
            continue
        new_dir = ROOT / f'Season {ns:02d}'
        new_stem = f'{SHOW} - S{ns:02d}E{ne:02d} - {title}'
        def tail(f):   # nur die Endung(en) übernehmen, nie den alten Titel (sonst 'S07E06 - A - B.mkv', Fehler vom 03.11.)
            rest = f.name[len(old_stem):]
            return rest if rest.startswith('.') else ('.' + rest.split('.', 1)[1] if '.' in rest else '')
        targets = [(f, new_dir / (new_stem + tail(f))) for f in files if f.suffix.lower() != '.nfo']
        clash = [t for _, t in targets if t.exists() and t not in vacated]   # vacated: von früheren Schritten frei gemacht
        print(('' if apply else '[Probelauf] ') + f'S{os_:02d}E{oe:02d}  ->  S{ns:02d}E{ne:02d}  {title}'
              + (f'   [Ziel existiert: {clash[0].name}]' if clash else ''))
        if clash:
            continue
        vacated.update(f for f, _ in targets)
        if not apply:
            continue
        new_dir.mkdir(parents=True, exist_ok=True)
        for f, t in targets:
            f.rename(t)
        old_nfo = next((f for f in files if f.suffix.lower() == '.nfo'), None)
        if old_nfo:
            old_nfo.rename(old_nfo.with_name(old_nfo.name + '.alt'))   # alte NFO bleibt als .alt liegen (kein Löschen)
        nfo = E.build_episode_nfo(series, ns, ne, epg_title=info.get('title', ''), episode_overview=info.get('overview', ''))
        (new_dir / f'{new_stem}.nfo').write_text(nfo, encoding='utf-8')
        log.append(f'{old_dir.name}/{old_stem}  ->  {new_dir.name}/{new_stem}')
        done += 1
    if apply:
        (ROOT / '_zuordnung_2026-11-03.txt').write_text('\n'.join(log) + '\n', encoding='utf-8')
    print(f'{done} Folgen umgezogen' if apply else 'Probelauf beendet, nichts verändert')


main('--apply' in sys.argv)
