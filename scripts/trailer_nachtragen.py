#!/usr/bin/env python3
"""Trailer-Verweise in bestehende NFO-Dateien nachtragen (Issue #58).

Läuft standardmäßig als PROBELAUF: liest nur, ändert nichts. Erst mit --apply wird in die NFOs geschrieben,
und zwar nur die eine Zeile <trailer>…</trailer> (der Rest der Datei bleibt Byte für Byte unverändert);
vorher wird jede zu ändernde NFO in --backup-dir gesichert.

Ablauf je NFO:
  - Film (<movie>):  Kennung aus <tmdbid> bzw. <uniqueid type="tmdb"> → TMDb /movie/<id>/videos
  - Serie (<tvshow>): Kennung aus <uniqueid type="tvdb"> (Vorsatz 'series-' wird toleriert) → TVDb series/<id>/extended
  - hat die NFO schon einen <trailer> → bleibt unberührt
  - keine Kennung / nicht lesbar → nur in der Liste (nie geändert)

Beispiel Probelauf (ohne Netz, nur zählen):  trailer_nachtragen.py --roots /volume1/1/Filme /volume1/1/Serien
Mit Stichprobe aus TMDb/TVDb:                … --tmdb-key … --tvdb-key … --sample 40
"""
import argparse
import hashlib
import json
import os
import random
import re
import shutil
import sys
import time
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import enricher as E  # noqa: E402

SKIP_DIRS = {'@eaDir', '#recycle', '_Reste'}


def iter_nfos(roots):
    """Alle .nfo-Dateien unter den Wurzeln; @eaDir und Papierkorb werden nie betreten."""
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in filenames:
                if fn.lower().endswith('.nfo') and not (Path(dirpath) / fn).is_symlink():
                    yield Path(dirpath) / fn


def classify(path: Path):
    """-> dict(kind, id, has_trailer, status). kind: movie|tvshow|other; status: ok|unlesbar|keine_kennung|hat_trailer."""
    try:
        raw = path.read_bytes()
        text = raw.decode('utf-8-sig')
        root = ET.fromstring(text)
    except Exception:
        return {'kind': 'other', 'id': '', 'status': 'unlesbar'}
    kind = {'movie': 'movie', 'tvshow': 'tvshow'}.get(root.tag)
    if not kind:
        return {'kind': 'other', 'id': '', 'status': 'ignoriert'}
    if (root.findtext('trailer') or '').strip():
        return {'kind': kind, 'id': '', 'status': 'hat_trailer'}
    meta = {'titles': [t for t in ((root.findtext('title') or '').strip(), (root.findtext('originaltitle') or '').strip()) if t],
            'year': (root.findtext('year') or '').strip()[:4]}
    ident = ''
    if kind == 'movie':
        ident = (root.findtext('tmdbid') or '').strip()
        for u in root.findall('uniqueid'):
            if not ident and (u.get('type') or '').lower() == 'tmdb':
                ident = (u.text or '').strip()
    else:
        for u in root.findall('uniqueid'):
            if (u.get('type') or '').lower() == 'tvdb':
                ident = (u.text or '').strip()
        ident = re.sub(r'^series-', '', ident)
    if not ident.isdigit():
        return {'kind': kind, 'id': '', 'status': 'keine_kennung', **meta}
    return {'kind': kind, 'id': ident, 'status': 'ok', **meta}


def movie_id_matches(tmdb, c) -> bool:
    """Gegenprobe: gehört die <tmdbid> wirklich zu diesem Film (Titel und Jahr)? Schützt vor Serien-Nummern
    und falschen Treffern in alten NFOs — sonst bekäme der Film den Trailer eines fremden Films."""
    d = tmdb._get(f"/movie/{int(c['id'])}")
    year = (d.get('release_date') or '')[:4]
    if c.get('year') and year and c['year'] != year:
        return False
    theirs = {E._norm_name(d.get('title') or ''), E._norm_name(d.get('original_title') or '')} - {''}
    mine = {E._norm_name(t) for t in c.get('titles', [])} - {''}
    return bool(theirs & mine)


def insert_trailer(path: Path, tag: str, backup_dir: Path) -> bool:
    """Fügt <trailer> vor dem schließenden Wurzel-Tag ein. Sicherung zuerst; True, wenn geschrieben."""
    raw = path.read_bytes()
    bom = b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b''
    text = raw[len(bom):].decode('utf-8')
    m = list(re.finditer(r'</(movie|tvshow)>\s*$', text))
    if not m or '<trailer' in text:
        return False
    pos = m[-1].start()
    eol = '\r\n' if '\r\n' in text else '\n'
    new = text[:pos] + f'  <trailer>{escape(tag)}</trailer>{eol}' + text[pos:]
    ET.fromstring(new)  # muss weiterhin gültiges XML sein, sonst nichts schreiben
    # Sicherungsname: Hash des vollen Pfads (kollisionsfrei) + lesbarer Dateiname; Zuordnung steht in index.jsonl
    backup = backup_dir / (hashlib.sha1(str(path).encode('utf-8')).hexdigest()[:12] + '_' + re.sub(r'[^A-Za-z0-9._-]+', '_', path.name) + '.bak')
    if backup.exists():
        raise FileExistsError(f'Sicherung existiert schon (wird nie überschrieben): {backup}')
    backup_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, backup)
    with open(backup_dir / 'index.jsonl', 'a', encoding='utf-8') as idx:
        idx.write(json.dumps({'sicherung': backup.name, 'original': str(path)}, ensure_ascii=False) + '\n')
    st = path.stat()
    tmp = path.with_name(path.name + '.tmp')
    try:
        tmp.write_bytes(bom + new.encode('utf-8'))
        shutil.copymode(path, tmp)
        try:
            os.chown(tmp, st.st_uid, st.st_gid)   # Besitzer behalten (z. B. Ruben statt root); klappt nicht überall
        except OSError:
            pass
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--roots', nargs='+', required=True, help='Ordner mit Film-/Serien-NFOs (rekursiv)')
    ap.add_argument('--tmdb-key', default=os.environ.get('TMDB_API_KEY'))
    ap.add_argument('--tvdb-key', default=os.environ.get('TVDB_API_KEY'))
    ap.add_argument('--sample', type=int, default=0, help='Probelauf: so viele Kandidaten bei TMDb/TVDb nachschlagen (0 = keine)')
    ap.add_argument('--apply', action='store_true', help='WIRKLICH schreiben (nur nach Freigabe!)')
    ap.add_argument('--backup-dir', help='Pflicht bei --apply: dauerhafter Ordner für die Sicherungen (nicht /tmp)')
    ap.add_argument('--report', help='Kandidatenliste (JSON Lines) hierhin schreiben')
    ap.add_argument('--limit', type=int, default=0, help='Höchstens so viele Kandidaten bearbeiten (nur zum Testen)')
    a = ap.parse_args()
    if a.apply and a.sample:
        ap.error('--apply und --sample passen nicht zusammen (--sample gilt nur im Probelauf; zum Begrenzen --limit nehmen)')
    if a.apply and not a.backup_dir:
        ap.error('--apply braucht --backup-dir (dauerhafter Ordner, nicht /tmp)')

    counts = {}
    cands = []
    for p in iter_nfos([Path(r) for r in a.roots]):
        c = classify(p)
        key = f"{c['kind']}:{c['status']}"
        counts[key] = counts.get(key, 0) + 1
        if c['status'] == 'ok':
            cands.append((p, c))
    print('Zählung (Art:Status → Anzahl)')
    for k in sorted(counts):
        print(f'  {k:24} {counts[k]}')

    todo = cands
    if a.apply:
        if a.limit:
            todo = cands[:a.limit]
    elif a.sample:
        random.seed(1)
        todo = random.sample(cands, min(a.sample, len(cands)))
    else:
        todo = []
    if a.report:
        Path(a.report).write_text(''.join(json.dumps({'nfo': str(p), **c}, ensure_ascii=False) + '\n' for p, c in cands))
    if not todo:
        print(f'\nKandidaten ohne Trailer, mit Kennung: {len(cands)}  (Probelauf: nichts nachgeschlagen, nichts geändert)')
        return

    tmdb = E.TMDb(a.tmdb_key) if a.tmdb_key else None
    tvdb = E.TVDb(a.tvdb_key) if a.tvdb_key else None
    found = missing = errors = written = mismatch = 0
    for p, c in todo:
        try:
            if c['kind'] == 'movie' and tmdb:
                if not movie_id_matches(tmdb, c):
                    mismatch += 1
                    print(f'  [Kennung passt nicht zum Film, übersprungen] {p}')
                    continue
                tag = E.tmdb_trailer_tag(tmdb.movie_videos(int(c['id'])))
            elif c['kind'] == 'tvshow' and tvdb:
                tag = E.youtube_trailer_tag((tvdb.series_details(int(c['id'])) or {}).get('trailers'))
            else:
                continue
        except Exception as e:
            errors += 1
            print(f'  [Fehler] {p}: {e}')
            continue
        if not tag:
            missing += 1
            continue
        found += 1
        if a.apply:
            try:
                if insert_trailer(p, tag, Path(a.backup_dir)):
                    written += 1
                    print(f'  [ergänzt] {p}')
            except Exception as e:   # ein Fehler (SMB, Rechte, Sicherung) stoppt nicht den ganzen Lauf
                errors += 1
                print(f'  [Fehler beim Schreiben, Datei unverändert] {p}: {e}')
        time.sleep(0.05)
    prefix = '' if a.apply else '[Probelauf] '
    print(f'\n{prefix}nachgeschlagen: {len(todo)}  Trailer gefunden: {found}  keiner gefunden: {missing}  Kennung passt nicht: {mismatch}  Fehler: {errors}'
          + (f'  geschrieben: {written}' if a.apply else '  (nichts geändert)'))
    if not a.apply and todo:
        print(f'Hochgerechnet auf alle {len(cands)} Kandidaten: ca. {round(len(cands) * found / max(1, len(todo)))} bekämen einen Trailer.')


if __name__ == '__main__':
    main()
