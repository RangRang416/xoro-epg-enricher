#!/usr/bin/env python3
"""
Folgen-Beschreibungen reparieren (#29): Folgen-NFOs, die nur den Serientitel als Titel tragen
(oder keinen Titel/Text), bekommen Titel und Handlung der Folge von TVDb - deutsch, wenn es eine
deutsche Übersetzung gibt. Alles andere in der Serie bleibt unberührt.

  python3 repair_episode_nfos.py --show-dir /volume1/1/Serien/Wednesday --tvdb-key ...           # Probelauf
  python3 repair_episode_nfos.py --show-dir ... --tvdb-key ... --apply --backup-dir /pfad/zur/sicherung

Staffel/Folge kommen aus der NFO selbst (<season>/<episode>), sonst aus dem Dateinamen.
Vor dem Überschreiben wird die alte NFO in --backup-dir gesichert (gleiche Ordnerstruktur).
Nur Python-stdlib; nutzt TVDb- und NFO-Helfer aus enricher.py (im selben Ordner).
"""

import argparse
import re
import shutil
import sys
import time
from pathlib import Path

import enricher as E


def episode_text(tvdb, tvdb_id: int, season: int, episode: int) -> dict:
    """{'title','overview','de'}: Titel/Text der Folge; de=True nur, wenn Titel UND Text deutsch sind."""
    data = tvdb._get(f'/series/{tvdb_id}/episodes/default', season=season, episodeNumber=episode)
    eps = (data.get('data') or {}).get('episodes') or []
    if not eps:
        return {}
    ep = eps[0]
    res = {'title': ep.get('name') or '', 'overview': ep.get('overview') or '', 'de': False}
    try:
        de = (tvdb._get(f'/episodes/{ep["id"]}/translations/deu').get('data')) or {}
        if de.get('name') or de.get('overview'):
            res['title'] = de.get('name') or res['title']
            res['overview'] = de.get('overview') or res['overview']
            res['de'] = bool(de.get('name') and de.get('overview'))
    except Exception:
        pass
    return res


def read_nfo(path: Path):
    try:
        root = E._ET.parse(path).getroot()
    except Exception:
        return None
    if root.tag != 'episodedetails':
        return None
    return {k: (root.findtext(k) or '').strip() for k in ('title', 'showtitle', 'season', 'episode', 'plot', 'year')}


def needs_repair(info: dict) -> bool:
    """Titel fehlt oder ist nur der Serienname = Folge nicht beschrieben."""
    t = info['title']
    return not t or E._norm_name(t) == E._norm_name(info['showtitle'])


def season_episode(info: dict, nfo: Path):
    if info['season'].isdigit() and info['episode'].isdigit():
        return int(info['season']), int(info['episode'])
    s, e = E.parse_se_from_filename(nfo.stem)
    return (s, e) if s and e else (None, None)


def show_info(show_dir: Path):
    nfo = show_dir / 'tvshow.nfo'
    try:
        root = E._ET.parse(nfo).getroot()
    except Exception:
        return None, '', ''
    tid = None
    for uid in root.findall('uniqueid'):
        t = re.sub(r'^series-', '', (uid.text or '').strip())
        if t.isdigit():
            tid = int(t)
            break
    return tid, (root.findtext('title') or show_dir.name).strip(), (root.findtext('year') or '').strip()


def repair_show(show_dir: Path, tvdb, apply: bool, backup_dir, stats: dict, text_fn=episode_text, pause=0.3):
    tvdb_id, name, year = show_info(show_dir)
    if not tvdb_id:
        print(f'[{show_dir.name}] keine TVDb-ID in tvshow.nfo — übersprungen')
        stats['serie_ohne_id'] += 1
        return
    stub = {'id': tvdb_id, 'name': name, 'year': year}
    for nfo in sorted(show_dir.rglob('*.nfo')):
        if nfo.name == 'tvshow.nfo' or '@eaDir' in nfo.parts:
            continue
        info = read_nfo(nfo)
        if info is None:
            continue
        if not needs_repair(info):
            stats['in_ordnung'] += 1
            continue
        season, ep = season_episode(info, nfo)
        if season is None:
            print(f'  {nfo.name}: Staffel/Folge nicht erkennbar — übersprungen')
            stats['unklar'] += 1
            continue
        try:
            t = text_fn(tvdb, tvdb_id, season, ep)
        except Exception as e:
            print(f'  {nfo.name}: TVDb-Fehler: {e}')
            stats['fehler'] += 1
            continue
        if not t or not t.get('title'):
            print(f'  {nfo.name}: S{season:02d}E{ep:02d} bei TVDb nicht gefunden — übersprungen')
            stats['nicht_gefunden'] += 1
            continue
        lang = 'de' if t['de'] else 'EN (keine deutsche Übersetzung)'
        print(f'{"" if apply else "[Probelauf] "}{nfo.name}\n    S{season:02d}E{ep:02d}: "{info["title"]}" -> "{t["title"]}" [{lang}]')
        stats['repariert' if apply else 'geplant'] += 1
        stats['deutsch' if t['de'] else 'englisch'] += 1
        if apply:
            if backup_dir:
                target = Path(backup_dir) / nfo.relative_to(show_dir.parent)
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    shutil.copy2(nfo, target)
            new = E.build_episode_nfo(stub, season, ep, epg_title=t['title'], episode_overview=t['overview'])
            nfo.write_text(new, encoding='utf-8')
        time.sleep(pause)


def main():
    ap = argparse.ArgumentParser(description='Folgen-Beschreibungen reparieren (#29)')
    ap.add_argument('--show-dir', required=True, action='append', help='Serienordner (mehrfach möglich)')
    ap.add_argument('--tvdb-key', required=True)
    ap.add_argument('--apply', action='store_true', help='Wirklich schreiben (ohne: Probelauf)')
    ap.add_argument('--backup-dir', help='Sicherung der alten NFOs (Pflicht mit --apply)')
    a = ap.parse_args()
    if a.apply and not a.backup_dir:
        sys.exit('--apply braucht --backup-dir')
    tvdb = E.TVDb(a.tvdb_key)
    stats = {k: 0 for k in ('geplant', 'repariert', 'deutsch', 'englisch', 'in_ordnung', 'unklar', 'nicht_gefunden', 'fehler', 'serie_ohne_id')}
    for d in a.show_dir:
        p = Path(d)
        if not p.is_dir():
            sys.exit(f'Ordner nicht gefunden: {p}')
        repair_show(p, tvdb, a.apply, a.backup_dir, stats)
    print('\nErgebnis:', ', '.join(f'{k}={v}' for k, v in stats.items()))


if __name__ == '__main__':
    main()
