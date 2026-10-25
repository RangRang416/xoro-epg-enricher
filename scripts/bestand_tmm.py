#!/usr/bin/env python3
"""
Bestandsserien reparieren (#53 / #29) mit tinyMediaManager PRO (TheTVDB, deutsch).

tinyMediaManager arbeitet NIE direkt auf der NAS. Ablauf je Serie:

  plan   Sandbox mit Platzhalter-Videos (gleiche Namen) bauen, tMM scrapen + umbenennen lassen,
         Zuordnung alt -> neu errechnen, Bericht + plan.json schreiben. Auf der NAS wird nichts verändert.
  apply  Plan auf der NAS ausführen: der alte Serienordner geht KOMPLETT in die Quarantäne
         (Eingang/_Reste/Bestand-<Datum>/<Serie> — nichts wird gelöscht), Videos/Untertitel kommen in die
         neue Struktur (Serie/Season NN/Serie - SxxEyy - Titel.ext), neue NFOs/Bilder werden hochgeladen,
         Jellyfin wird gezielt für diese Serie informiert (kein Voll-Scan).

Rückgängig: apply schreibt vorab ein UNDO-Skript (<Quarantäne>/<Serie>.UNDO.sh, Kopie in <work>/plans/):
  es schiebt die Videos/Untertitel zurück in den alten Ordner und diesen an seinen Platz. NICHT von Hand
  den Quarantäne-Ordner zurückschieben und den neuen löschen — die Videos liegen dann nur im neuen Ordner.

Verwendung:
  python3 scripts/bestand_tmm.py plan  "Wayward.Unberechenbar"
  python3 scripts/bestand_tmm.py apply "Wayward.Unberechenbar"      # nur nach Durchsicht des Plans

Voraussetzungen: ssh-Alias 'synology', tinyMediaManager (Linux, PRO-Lizenz in dessen data-Ordner),
Jellyfin-Schlüssel in $JELLYFIN_KEY (nur für apply). Nur Python-stdlib.
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import inbox  # noqa: E402  (Jellyfin-Helfer)

VIDEO_EXTS = {'.mkv', '.avi', '.mp4', '.m4v', '.mpg', '.mpeg', '.ts', '.m2ts', '.vob', '.wmv', '.mov', '.webm',
              '.flv', '.divx', '.rmvb', '.iso', '.ogm', '.3gp'}
SUB_EXTS = {'.srt', '.ass', '.sub', '.idx', '.sup'}
SERIES_ROOT = '/volume1/1/Serien'
QUARANTINE_ROOT = '/volume1/1/Eingang/_Reste'
JF_ROOT = '/bestehende-serien'
MARK = b'TMMID-'
SKIP_NEW = {'theme.mp3'}           # von tMM mitgeladen, in der Bibliothek unerwünscht


# ── NAS ───────────────────────────────────────────────────────────────────────

def ssh(cmd: str, stdin: bytes = None, nas: str = 'synology', timeout: int = 600) -> str:
    r = subprocess.run(['ssh', '-o', 'ConnectTimeout=30', nas, cmd], input=stdin,
                       capture_output=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f'ssh fehlgeschlagen ({r.returncode}): {r.stderr.decode(errors="replace")[:500]}')
    return r.stdout.decode(errors='surrogateescape')


def list_remote(series: str, nas: str) -> list:
    out = ssh(f'cd {shlex.quote(SERIES_ROOT)} && find {shlex.quote(series)} -type f -not -path "*@eaDir*" '
              f'-not -path "*#recycle*" -printf "%P\\t%s\\n"', nas=nas)
    rows = []
    for line in out.splitlines():
        rel, _, size = line.rpartition('\t')
        if rel:
            rows.append((rel, int(size or 0)))
    return rows


def remote_tvdb_id(series: str, nas: str):
    try:
        out = ssh(f'cat {shlex.quote(SERIES_ROOT + "/" + series + "/tvshow.nfo")}', nas=nas)
    except RuntimeError:
        return None
    for m in re.finditer(r'<uniqueid[^>]*>\s*(?:series-)?(\d+)\s*</uniqueid>', out):
        return int(m.group(1))
    return None


# ── Sandbox + tinyMediaManager ────────────────────────────────────────────────

_SAMPLE_WORD = re.compile(r'(?i)(^|[-._ \[(])sample([-._ \])]|$)')
SAMPLE_MAX = 200 * 1024 * 1024
BIG_LEFTOVER = 50 * 1024 * 1024        # nicht mitgenommene Datei darüber -> Sperre (echter Inhalt?)


def is_sample(rel: str, size: int = 0) -> bool:
    """Sample = liegt in einem Sample-Ordner ODER trägt 'sample' als eigenes Wort im Namen und ist klein."""
    parts = [p.lower() for p in Path(rel).parts]
    if any(p in ('sample', 'samples') for p in parts[:-1]):
        return True
    return bool(_SAMPLE_WORD.search(Path(rel).stem)) and size < SAMPLE_MAX


def _safe(series: str) -> str:
    return re.sub(r'\W+', '_', series) + '_' + hashlib.sha1(series.encode()).hexdigest()[:6]


def build_sandbox(series: str, rows: list, sb_root: Path) -> dict:
    """Platzhalter-Videos/Untertitel mit gleichen Namen. Alte NFOs/Bilder werden NICHT kopiert (sauberes Scrapen)."""
    if sb_root.exists():
        shutil.rmtree(sb_root)
    show = sb_root / series
    show.mkdir(parents=True)
    ids = {}
    for rel, size in sorted(rows):
        ext = Path(rel).suffix.lower()
        if ext not in VIDEO_EXTS or is_sample(rel, size):     # Untertitel behandelt plan_subtitles() selbst
            continue
        key = f'{MARK.decode()}{len(ids):06d}'
        ids[key] = rel
        p = show / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes((key + '\n').encode().ljust(2048, b'\0'))
    return ids


def run_tmm(sb_root: Path, tmm: Path, data: Path, log: Path):
    settings = data / 'tvShows.json'
    cfg = json.loads(settings.read_text(encoding='utf-8'))
    cfg['tvShowDataSource'] = [str(sb_root)]
    cfg['scraper'] = 'tvdb'
    settings.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding='utf-8')
    for f in data.glob('tvshows.db*'):      # frische Datenbank: nur diese Serie, nie alte Testserien
        f.unlink()
    r = subprocess.run([str(tmm), 'tvshow', '-u', '--scrapeAll', '--renameAll'], cwd=tmm.parent,
                       capture_output=True, timeout=3600)
    log.write_bytes(r.stdout + b'\n' + r.stderr)
    text = log.read_text(errors='replace')
    m = re.search(r'TV shows found: (\d+)', text)
    if not m or int(m.group(1)) != 1:
        raise RuntimeError(f'tMM hat nicht genau 1 Serie gefunden ({m.group(1) if m else "?"}) — Abbruch. Log: {log}')
    if "with 'tvdb'" not in text:
        raise RuntimeError(f'tMM hat nicht über TheTVDB gescrapt (Lizenz/Einstellung?) — Abbruch. Log: {log}')


def _read_marker(p: Path):
    try:
        with open(p, 'rb') as fh:
            head = fh.read(len(MARK) + 6)
    except OSError:
        return None
    return head.decode(errors='replace').strip('\0\n') if head.startswith(MARK) else None


def _nfo_field(nfo: Path, tag: str):
    m = re.search(rf'<{tag}>([^<]*)</{tag}>', nfo.read_text(encoding='utf-8', errors='replace'))
    return m.group(1).strip() if m else None


LANG = {'eng': 'en', 'en': 'en', 'ger': 'de', 'deu': 'de', 'de': 'de', 'german': 'de',
        'fre': 'fr', 'fra': 'fr', 'spa': 'es', 'ita': 'it'}


def sub_suffix(stem: str) -> str:
    """'tv4a-x.s01e01-1080p-eng-forced' -> 'en.forced'. Ohne Sprachangabe: deutsch (Release 'German')."""
    toks = re.split(r'[-._ ]+', stem.lower())
    lang = next((LANG[t] for t in reversed(toks) if t in LANG), 'de')
    return lang + ('.forced' if 'forced' in toks else '')


_TOKEN_RE = re.compile(r'(?<![A-Za-z0-9])[Ss](\d{1,2})[Ee](\d{1,3})(?!\d)')


def _ep_token(rel: str):
    """'…s01e02-1080p-eng.idx' -> 'S01E02' (Dateiname zuerst, dann Elternordner)."""
    for part in reversed(Path(rel).parts):
        m = _TOKEN_RE.search(part)
        if m:
            return f'S{int(m.group(1)):02d}E{int(m.group(2)):02d}'
    return None


def plan_subtitles(plan: dict, rows: list):
    """Untertitel neben die umbenannte Folge legen: '<neuer Folgenname>.<sprache>[.forced].<ext>'."""
    video_new = {}
    for old, new in plan['moves']:
        if Path(old).suffix.lower() in VIDEO_EXTS and (tok := _ep_token(old)):
            video_new.setdefault(tok, new)
    taken = set()
    for rel, size in sorted(rows):
        if Path(rel).suffix.lower() not in SUB_EXTS or is_sample(rel, size):
            continue
        new_video = video_new.get(_ep_token(rel))
        if not new_video:
            plan['unmatched'].append(rel)
            continue
        new = f'{Path(new_video).with_suffix("")}.{sub_suffix(Path(rel).stem)}{Path(rel).suffix.lower()}'
        if new in taken:
            plan['blocking'].append(f'Untertitel-Name doppelt: {new}')
        taken.add(new)
        plan['moves'].append([rel, new])
    if any(Path(r).suffix.lower() in SUB_EXTS and not is_sample(r, sz) and sub_suffix(Path(r).stem) == 'de'
           and not re.search(r'(?i)(ger|deu|german)', Path(r).stem) for r, sz in rows):
        plan['warnings'].append('Untertitel ohne Sprachangabe wurden als deutsch (.de) benannt')


def finalize_plan(plan: dict, rows: list):
    """Absicherungen: Dateiliste merken, nicht mitgenommene Dateien auflisten, Ziele auf Eindeutigkeit prüfen."""
    plan['rows'] = [[r, s] for r, s in sorted(rows)]
    if any(re.search('[\udc80-\udcff]', r) for r, _ in rows):
        plan['blocking'].append('Dateiname ist kein gültiges UTF-8 — manuell prüfen')
    carried = {o for o, _ in plan['moves']} | set(plan['unmatched'])
    left = [[r, sz] for r, sz in sorted(rows) if r not in carried]
    plan['not_carried'] = left
    big = [r for r, sz in left if sz > BIG_LEFTOVER and not is_sample(r, sz)]
    if big:
        plan['blocking'].append(f'{len(big)} große Dateien werden NICHT übernommen (blieben in der Quarantäne), z. B. {big[0]}')
    targets = [n for _, n in plan['moves']] + list(plan['unmatched'])
    seen, dup = set(), set()
    for t in targets:
        (dup if t in seen else seen).add(t)
    if dup:
        plan['blocking'].append(f'{len(dup)} Zielpfade doppelt belegt, z. B. {sorted(dup)[0]}')
    clash = set(targets) & {f.split('/', 1)[1] for f in plan['new_files']}
    if clash:
        plan['blocking'].append(f'{len(clash)} Zielpfade kollidieren mit neuen NFOs/Bildern, z. B. {sorted(clash)[0]}')


def collect_plan(series: str, ids: dict, sb_root: Path, old_tvdb) -> dict:
    shows = [d for d in sb_root.iterdir() if d.is_dir() and not d.name.startswith('.')]
    if len(shows) != 1:
        raise RuntimeError(f'Erwartet 1 Serienordner im Ergebnis, gefunden: {[d.name for d in shows]}')
    show = shows[0]
    plan = {'old_show': series, 'new_show': show.name, 'moves': [], 'unmatched': [], 'new_files': [],
            'warnings': [], 'blocking': []}
    seen = set()
    for p in sorted(show.rglob('*')):
        if not p.is_file() or '.deletedByTMM' in p.parts:
            continue
        rel_new = str(p.relative_to(show))
        key = _read_marker(p)
        if key:
            seen.add(key)
            old_rel = ids[key]
            if any(part.startswith('Season ') for part in Path(rel_new).parts[:-1]):
                plan['moves'].append([old_rel, rel_new])
            else:
                plan['unmatched'].append(old_rel)       # keine Staffel/Folge erkannt: bleibt an alter Stelle
        elif p.name not in SKIP_NEW:
            plan['new_files'].append(f'{show.name}/{rel_new}')
    missing = set(ids) - seen
    if missing:
        plan['blocking'].append(f'{len(missing)} Dateien nach tMM-Lauf nicht mehr auffindbar')
    nfo = show / 'tvshow.nfo'
    if nfo.exists():
        found = re.findall(r'type="tvdb"[^>]*>(\d+)<', nfo.read_text(encoding='utf-8', errors='replace'))
        plan['match'] = {'title': _nfo_field(nfo, 'title'), 'year': _nfo_field(nfo, 'year'),
                         'tvdb': found[0] if found else None, 'old_tvdb': old_tvdb}
        new_tvdb = plan['match']['tvdb']
        if old_tvdb and new_tvdb and int(new_tvdb) != int(old_tvdb):
            plan['blocking'].append(f'Andere Serie erkannt: alte TVDB-ID {old_tvdb}, neue {new_tvdb} ({plan["match"]["title"]})')
    else:
        plan['blocking'].append('tMM hat keine Serie erkannt (kein tvshow.nfo)')
    no_text = [f for f in plan['new_files'] if f.endswith('.nfo') and not f.endswith('tvshow.nfo')
               and '<plot>' not in (sb_root / f).read_text(encoding='utf-8', errors='replace')]
    if no_text:
        plan['warnings'].append(f'{len(no_text)} Folgen-NFOs ohne Beschreibung')
    if plan['unmatched']:
        plan['warnings'].append(f'{len(plan["unmatched"])} Videos/Untertitel ohne erkannte Folge (bleiben an alter Stelle)')
    return plan


def watched_count(series: str, jf_url: str, jf_key: str):
    """Wie viele Folgen hat Ruben als gesehen markiert (geht beim Umbenennen des Serienordners verloren)."""
    try:
        users = inbox._jf(jf_url, jf_key, '/Users') or []
        uid = next((u['Id'] for u in users if u['Name'] == 'Ruben'), None)
        res = inbox._jf(jf_url, jf_key, '/Items?Recursive=true&IncludeItemTypes=Series&Fields=Path&SearchTerm=' +
                        urllib.parse.quote(series.split('.')[0])) or {}
        sid = next((i['Id'] for i in res.get('Items', []) if i.get('Path') == f'{JF_ROOT}/{series}'), None)
        if not (uid and sid):
            return None
        eps = inbox._jf(jf_url, jf_key, f'/Items?ParentId={sid}&Recursive=true&IncludeItemTypes=Episode&Filters=IsPlayed&UserId={uid}') or {}
        return eps.get('TotalRecordCount', 0)
    except Exception:
        return None


# ── Befehle ───────────────────────────────────────────────────────────────────

def cmd_plan(a):
    work = Path(a.work)
    safe = _safe(a.series)
    rows = list_remote(a.series, a.nas)
    if not rows:
        sys.exit(f'Serienordner nicht gefunden oder leer: {a.series}')
    sb = work / 'sandbox' / safe
    ids = build_sandbox(a.series, rows, sb)
    print(f'Sandbox: {len(ids)} Videos/Untertitel (Samples und alte NFOs ausgelassen), tMM läuft ...')
    run_tmm(sb, Path(a.tmm), Path(a.tmm_data), work / f'{safe}.tmm.log')
    plan = collect_plan(a.series, ids, sb, remote_tvdb_id(a.series, a.nas))
    plan_subtitles(plan, rows)
    finalize_plan(plan, rows)
    plan['sandbox'] = str(sb)
    key = os.environ.get('JELLYFIN_KEY')
    if key:
        plan['watched'] = watched_count(a.series, a.jellyfin_url, key)
    (work / 'plans').mkdir(parents=True, exist_ok=True)
    out = work / 'plans' / f'{safe}.json'
    out.write_text(json.dumps(plan, indent=1, ensure_ascii=False), encoding='utf-8')
    m = plan.get('match', {})
    print(f'\nSerie:   {plan["old_show"]}  ->  {plan["new_show"]}')
    print(f'Erkannt: {m.get("title")} ({m.get("year")}), TVDB {m.get("tvdb")} (vorher {m.get("old_tvdb")})')
    print(f'Folgen:  {len(plan["moves"])} Dateien in Season-Ordner, {len(plan["unmatched"])} ohne Zuordnung, '
          f'{len(plan["new_files"])} neue NFOs/Bilder')
    if plan.get('watched') is not None:
        print(f'Gesehen: {plan["watched"]} Folgen als gesehen markiert (gehen beim Umbenennen verloren)')
    left = plan['not_carried']
    print(f'Quarantäne: {len(left)} Dateien bleiben im gesicherten alten Ordner '
          f'(davon {sum(1 for r, sz in left if is_sample(r, sz))} Samples, {sum(sz for _, sz in left) // 1024**2} MB)')
    for w in plan['warnings']:
        print('  Hinweis:', w)
    for b in plan['blocking']:
        print('  SPERRE: ', b)
    for old, new in plan['moves'][:4]:
        print(f'  {old}\n    -> {new}')
    print(f'\nPlan: {out}')


def _script(body: list) -> bytes:
    """Als Funktion verpackt: bash parst alles, bevor das erste Kommando läuft."""
    return ('main() {\nset -euo pipefail\n' + '\n'.join(body) + '\n}\nmain\n').encode(errors='surrogateescape')


def cmd_apply(a):
    work = Path(a.work)
    safe = _safe(a.series)
    plan = json.loads((work / 'plans' / f'{safe}.json').read_text(encoding='utf-8'))
    if plan['old_show'] != a.series:
        sys.exit('Plan gehört zu einer anderen Serie — abgebrochen.')
    done = work / 'plans' / f'{safe}.applied'
    if done.exists() and not a.force:
        sys.exit(f'Bereits angewendet (Quarantäne {done.read_text()}) — nicht erneut ausführen.')
    if plan['blocking'] and not a.force:
        sys.exit('Plan hat Sperren: ' + '; '.join(plan['blocking']))
    if sorted(map(tuple, list_remote(a.series, a.nas))) != sorted(map(tuple, plan['rows'])):
        sys.exit('Der Serienordner hat sich seit dem Plan verändert (neue/umbenannte Dateien) — Plan neu erstellen.')
    old, new = plan['old_show'], plan['new_show']
    q = f'{QUARANTINE_ROOT}/Bestand-{datetime.date.today().isoformat()}'
    S = shlex.quote
    sb = Path(plan['sandbox'])
    if not sb.is_dir():
        sys.exit(f'Sandbox fehlt: {sb} — Plan neu erstellen.')
    # Archiv zuerst bauen: scheitert das, ist auf der NAS noch nichts passiert.
    names = '\0'.join(plan['new_files']).encode()
    tar = subprocess.run(['tar', '-C', str(sb), '--null', '-T', '-', '-cf', '-'], input=names,
                         capture_output=True, check=True).stdout
    tar_file = work / 'plans' / f'{safe}.new.tar'
    tar_file.write_bytes(tar)
    pairs = [(o, n) for o, n in plan['moves']] + [(o, o) for o in plan['unmatched']]
    head = [f'S={S(SERIES_ROOT)}', f'Q={S(q)}']
    # Rückgängig-Skript: Videos zurück in den alten Ordner, neuen Rest beiseite, alten Ordner an seinen Platz.
    undo = head + [f'[ -d "$S"/{S(new)} ] || exit 5', f'[ -d "$Q"/{S(old)} ] || exit 6']
    undo += [f'mkdir -p "$Q"/{S(old)}/{S(str(Path(o).parent))}' for o in sorted({o for o, _ in pairs})
             if str(Path(o).parent) != '.']
    undo += [f'[ -e "$S"/{S(new)}/{S(n)} ] || {{ echo "fehlt: {n}" >&2; exit 7; }}' for _, n in pairs]
    undo += [f'mv "$S"/{S(new)}/{S(n)} "$Q"/{S(old)}/{S(o)}' for o, n in pairs]
    undo += [f'mv "$S"/{S(new)} "$Q"/{S(new)}.NEU-$(date +%H%M%S)', f'mv "$Q"/{S(old)} "$S"/{S(old)}']
    undo_bytes = _script(undo)
    (work / 'plans' / f'{safe}.UNDO.sh').write_bytes(undo_bytes)
    ssh(f'mkdir -p {S(q)} && cat > {S(q + "/" + old + ".UNDO.sh")}', stdin=undo_bytes, nas=a.nas)
    # Hauptskript: erst alles prüfen, dann verschieben.
    body = head + ['mkdir -p "$Q"', f'[ ! -e "$Q"/{S(old)} ] || {{ echo "Quarantäne existiert schon" >&2; exit 3; }}',
                   f'[ -d "$S"/{S(old)} ] || {{ echo "Serienordner fehlt" >&2; exit 5; }}']
    if new != old:
        body.append(f'[ ! -e "$S"/{S(new)} ] || {{ echo "Zielordner existiert schon" >&2; exit 4; }}')
    body += [f'[ -e "$S"/{S(old)}/{S(o)} ] || {{ echo "Quelle fehlt: {o}" >&2; exit 6; }}' for o, _ in pairs]
    body += [f'mv "$S"/{S(old)} "$Q"/{S(old)}', f'mkdir -p "$S"/{S(new)}']
    body += [f'mkdir -p "$S"/{S(new)}/{S(d)}' for d in sorted({str(Path(n).parent) for _, n in pairs}) if d != '.']
    body += [f'mv "$Q"/{S(old)}/{S(o)} "$S"/{S(new)}/{S(n)}' for o, n in pairs]
    ssh('bash -s', stdin=_script(body), nas=a.nas)
    done.write_text(q)
    print(f'Verschoben. Alter Ordner gesichert unter {q}/{old} (Rückgängig: {q}/{old}.UNDO.sh)')
    try:
        ssh(f'cd {S(SERIES_ROOT)} && tar -xf -', stdin=tar, nas=a.nas)
    except RuntimeError as e:
        sys.exit(f'Upload der neuen NFOs/Bilder fehlgeschlagen: {e}\nNachholen: ssh {a.nas} "cd {SERIES_ROOT} && tar -xf -" < {tar_file}')
    print(f'{len(plan["new_files"])} neue NFOs/Bilder hochgeladen.')
    key = os.environ.get('JELLYFIN_KEY')
    if not key:
        print('JELLYFIN_KEY fehlt — Jellyfin nicht informiert (der nächste Scan holt es nach).')
        return
    if new != old:      # gleicher Pfad: nicht als gelöscht melden, sonst legt Jellyfin die Serie neu an
        try:
            inbox._jf(a.jellyfin_url, key, '/Library/Media/Updated', 'POST',
                      {'Updates': [{'Path': f'{JF_ROOT}/{old}', 'UpdateType': 'Deleted'}]})
        except Exception as e:
            print('  Jellyfin (alter Pfad) nicht gemeldet:', e)
    ok = inbox.jellyfin_refresh_series(a.jellyfin_url, key, f'{JF_ROOT}/{new}', plan['match']['title'])
    print('Jellyfin gezielt aufgefrischt.' if ok else 'Jellyfin: bitte Ergebnis prüfen.')


def main():
    ap = argparse.ArgumentParser(description='Bestandsserien mit tinyMediaManager reparieren (#53/#29)')
    ap.add_argument('command', choices=['plan', 'apply'])
    ap.add_argument('series', help='Serienordner unter /volume1/1/Serien')
    ap.add_argument('--nas', default='synology')
    ap.add_argument('--work', default='/root/tmm-work')
    ap.add_argument('--tmm', default='/root/tmm-test/app/tinyMediaManager/tinyMediaManager')
    ap.add_argument('--tmm-data', default='/root/.local/share/tinyMediaManager/data')
    ap.add_argument('--jellyfin-url', default='http://192.168.2.9:8096')
    ap.add_argument('--force', action='store_true', help='Plan trotz Sperren ausführen (nur nach Rücksprache)')
    a = ap.parse_args()
    (cmd_plan if a.command == 'plan' else cmd_apply)(a)


if __name__ == '__main__':
    main()
