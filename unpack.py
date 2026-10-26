#!/usr/bin/env python3
"""
unpack.py — mehrteilige RAR-Archive im Eingangsordner sicher auspacken (#53). NOTLÖSUNG: JDownloader packt
im Normalfall selbst aus; das hier greift nur bei Paketen, die >= 24 h komplett liegen (siehe inbox.py --unpack).

Die Archive stammen aus fremden Downloads, die NAS hat 1 GB RAM und ein altes unrar 5.70 (CVE-2022-30333:
Symlink-Pfadtraversal). Deshalb mehrere Verteidigungslinien, alle fail-closed:
  1. Nur VOLLSTÄNDIGE Pakete (Teile 1..n, keine .part/.!ut-Geschwister, nichts frisch, keine alte .rNN-Benennung).
  2. Vorher `unrar lt -v` lesen: genau n Volumes gelistet; je Eintrag genau EIN Typ (nur File/Directory);
     kein 'Target:' (Link-Ziel); keine Steuerzeichen/'..'/absolute Pfade im Namen; keine doppelten Dateinamen
     (Auspacken ist flach); entpackte Größe plausibel (kaum Kompression) und Platz mit Reserve vorhanden.
  3. Auspacken flach (`unrar e -ai`) in Temp-Ordner neben dem Paket, nice/ionice, Speicherdeckel, ohne stdin.
  4. Danach lstat jedes Eintrags: NUR normale Dateien, sonst Temp-Ordner weg und Fehler.
  5. Archive werden NIE gelöscht und nie überschrieben: nach _Reste/Archive-<Datum>/<name>[_n]/ verschoben.
  6. Fehlgeschlagene Pakete werden vermerkt und erst nach einer Änderung erneut versucht.
Nur Python-stdlib.
"""

import datetime
import json
import os
import re
import shutil
import stat
import subprocess
import time
from pathlib import Path

TMP_PREFIX = '.entpacken-'
ARCHIVE_DIRNAME = 'Archive'
FAILED_FILE = 'entpacken-fehler.json'      # in _Reste/
UNFINISHED_EXTS = {'.part', '.!ut', '.crdownload', '.tmp', '.jdownloader'}
SKIP_DIRS = {'_reste', '@eadir', '#recycle'}
RESERVE_BYTES = 5 * 1024**3                # so viel Platz muss nach dem Auspacken noch frei sein
MAX_RATIO = 1.5                            # entpackt/gepackt; Video lässt sich kaum komprimieren
MEM_LIMIT = 700 * 1024**2                  # unrar-Speicherdeckel (RAR5-Wörterbuch bis 1 GB, NAS hat 1 GB RAM)

_PART_RE = re.compile(r'^(?P<base>.+)\.part(?P<n>\d+)\.rar$', re.I)
_SOLO_RE = re.compile(r'^(?P<base>.+)\.rar$', re.I)
_OLD_RE = re.compile(r'^(?P<base>.+)\.r\d{2,}$', re.I)
_NAME_RE = re.compile(r'^\s*Name:\s?(.*)$')
_TYPE_RE = re.compile(r'^\s*Type:\s*(.*?)\s*$')
_SIZE_RE = re.compile(r'^\s*Size:\s*(\d+)\s*$')
_TARGET_RE = re.compile(r'^\s*(?:Target|Link target|Link):', re.I)
_ARCHIVE_RE = re.compile(r'^\s*Archive:\s')
_CTRL_RE = re.compile('[\x00-\x1f\x7f\x80-\x9f  ]')


class ArchiveSet:
    def __init__(self, directory: Path, base: str):
        self.directory, self.base = directory, base
        self.parts = {}          # Teilnummer -> Pfad (Einzel-RAR: Nummer 1)

    @property
    def first(self) -> Path:
        return self.parts[min(self.parts)]

    def paths(self):
        return [self.parts[n] for n in sorted(self.parts)]

    def key(self, inbox: Path) -> str:
        return str(self.directory.relative_to(inbox) / self.base)

    def signature(self):
        sig = []
        for p in self.paths():
            try:
                st = p.stat()
                sig.append([p.name, st.st_size, int(st.st_mtime)])
            except OSError:
                sig.append([p.name, -1, -1])
        return sig


# ── Pakete finden / Bereitschaft ──────────────────────────────────────────────

def find_sets(inbox: Path):
    """Alle RAR-Pakete im Eingang (rekursiv, Groß-/Kleinschreibung egal), ohne _Reste/@eaDir/Temp-Ordner."""
    sets = {}
    for p in sorted(inbox.rglob('*')):
        if p.suffix.lower() != '.rar':
            continue
        try:
            rel = p.relative_to(inbox)
            if not p.is_file() or p.is_symlink() or any(
                    x.lower() in SKIP_DIRS or x.startswith(TMP_PREFIX) or x.startswith('@') for x in rel.parts[:-1]):
                continue
        except (OSError, ValueError):
            continue
        m = _PART_RE.match(p.name)
        if m:
            base, num = m.group('base'), int(m.group('n'))
        else:
            m = _SOLO_RE.match(p.name)
            base, num = m.group('base'), 1
        s = sets.setdefault((p.parent, base.lower()), ArchiveSet(p.parent, base))
        s.parts[num] = p
    return list(sets.values())


def _siblings(s: ArchiveSet):
    try:
        return [x for x in s.directory.iterdir() if x.is_file()]
    except OSError:
        return None


def set_ready(s: ArchiveSet, min_age: int, now: float = None):
    """(True, '') oder (False, Grund). Prüft Vollständigkeit, Teil-Downloads, alte Benennung und Alter."""
    now = time.time() if now is None else now
    nums = sorted(s.parts)
    if nums != list(range(1, nums[-1] + 1)):
        return False, f'Teile unvollständig (vorhanden: {nums})'
    sib = _siblings(s)
    if sib is None:
        return False, 'Ordner nicht lesbar'
    prefix = s.base.lower() + '.'
    for x in sib:
        n = x.name.lower()
        if n.startswith(prefix) and x.suffix.lower() in UNFINISHED_EXTS:
            return False, f'Teil-Download läuft noch ({x.name})'
        if _OLD_RE.match(x.name) and x.name.lower().startswith(prefix):
            return False, 'alte RAR-Benennung (.r00) wird nicht unterstützt'
    for p in s.paths():
        try:
            st = p.stat()
        except OSError:
            return False, f'{p.name} nicht lesbar'
        if now - st.st_mtime < min_age:
            return False, f'{p.name} ist noch frisch'
        if st.st_size == 0:
            return False, f'{p.name} ist leer'
    return True, ''


# ── Inhaltsverzeichnis prüfen ─────────────────────────────────────────────────

def check_listing(text: str, volumes: int = None):
    """Prüft die Ausgabe von `unrar lt -v`. -> (ok, Grund, Info-Dict). Fail-closed.

    Wichtig: nur an '\\n' trennen (nicht splitlines — das trennt auch an \\x0b, \\x85, U+2028 ...), je Eintrag genau
    ein Type, Steuerzeichen im Namen sind verboten. `volumes`: erwartete Zahl der 'Archive:'-Zeilen."""
    lines = text.split('\n')
    if volumes is not None:
        seen = sum(1 for ln in lines if _ARCHIVE_RE.match(ln))
        if seen != volumes:
            return False, f'{seen} statt {volumes} Volumes gelistet', {}
    entries, cur = [], None
    for ln in lines:
        ln = ln.rstrip('\r')
        if _TARGET_RE.match(ln):
            return False, 'Eintrag mit Link-Ziel', {}
        m = _NAME_RE.match(ln)
        if m:
            cur = {'name': m.group(1), 'type': None, 'size': None}
            entries.append(cur)
            continue
        m = _TYPE_RE.match(ln)
        if m:
            if cur is None or cur['type'] is not None:
                return False, 'Typ-Zeile ohne passenden Namen oder doppelt', {}
            cur['type'] = m.group(1)
            continue
        m = _SIZE_RE.match(ln)
        if m and cur is not None and cur['size'] is None:
            cur['size'] = int(m.group(1))
    if not entries:
        return False, 'Inhaltsverzeichnis leer/nicht lesbar', {}
    files = {}      # Name -> Größe (mit -v taucht eine geteilte Datei in jedem Volume wieder auf)
    for e in entries:
        name, typ = e['name'], (e['type'] or '').lower()
        if typ not in ('file', 'directory'):
            return False, f'Eintrag mit Typ "{e["type"]}"', {}
        parts = re.split(r'[\\/]', name)
        if (not name or _CTRL_RE.search(name) or name.startswith(('/', '\\')) or re.match(r'^[A-Za-z]:', name)
                or '..' in parts or '\\' in name):
            return False, f'Unzulässiger Pfad im Archiv: {name!r}', {}
        if typ == 'file':
            if name in files and files[name] is not None and e['size'] is not None:
                files[name] = max(files[name], e['size'])
            else:
                files.setdefault(name, e['size'])
    if not files:
        return False, 'Archiv enthält keine Datei', {}
    if any(sz is None for sz in files.values()):
        return False, 'Dateigröße fehlt im Inhaltsverzeichnis', {}
    bases = [re.split(r'[\\/]', n)[-1].lower() for n in files]
    if len(set(bases)) != len(bases):
        return False, 'gleiche Dateinamen in verschiedenen Archivordnern (Auspacken ist flach)', {}
    return True, '', {'names': sorted(files), 'basenames': bases, 'count': len(files), 'unpacked': sum(files.values())}


# ── Ausführen ─────────────────────────────────────────────────────────────────

def _limit_memory():     # nur Linux; im Kindprozess vor exec
    import resource
    resource.setrlimit(resource.RLIMIT_AS, (MEM_LIMIT, MEM_LIMIT))


def _runner(cmd, timeout):
    return subprocess.run(cmd, capture_output=True, timeout=timeout, stdin=subprocess.DEVNULL,
                          preexec_fn=_limit_memory)


def _unique_dir(path: Path) -> Path:
    n, cand = 2, path
    while cand.exists():
        cand = path.with_name(f'{path.name}_{n}')
        n += 1
    return cand


def _only_regular_files(root: Path):
    """Jeder Eintrag unter root (rekursiv) muss eine normale Datei sein (lstat, folgt keinen Links)."""
    count = 0
    stack = [root]
    while stack:
        d = stack.pop()
        with os.scandir(d) as it:
            for e in it:
                mode = os.lstat(e.path).st_mode
                if stat.S_ISREG(mode):
                    count += 1
                else:
                    return None
    return count


def _already_there(s: ArchiveSet, basenames):
    """True, wenn die genannten Dateien (nach Basisnamen) schon neben dem Paket liegen — JDownloader war schneller."""
    dirs = [s.directory]
    try:
        dirs += [x for x in s.directory.iterdir() if x.is_dir() and not x.name.startswith((TMP_PREFIX, '@'))]
    except OSError:
        pass
    have = set()
    for d in dirs:
        try:
            have |= {x.name.lower() for x in d.iterdir() if x.is_file()}
        except OSError:
            pass
    return bool(basenames) and all(b in have for b in basenames)


def _stash(s: ArchiveSet, inbox: Path, today: str = None):
    day = today or datetime.date.today().isoformat()
    arch = _unique_dir(inbox / '_Reste' / f'{ARCHIVE_DIRNAME}-{day}' / s.base)
    arch.mkdir(parents=True)
    for p in s.paths():
        dst = arch / p.name
        if dst.exists():
            raise RuntimeError(f'Ziel existiert schon, nichts überschrieben: {dst}')
        shutil.move(str(p), str(dst))
    return arch


def unpack_set(s: ArchiveSet, inbox: Path, unrar: str = 'unrar', run=_runner, today: str = None):
    """Packt ein bereites Paket aus. -> (Ergebnis 'ok'|'fehler', Text, Release-Ordner|None)."""
    packed = sum(p.stat().st_size for p in s.paths())
    r = run([unrar, 'lt', '-v', '-c-', '-p-', str(s.first)], 600)
    if r.returncode != 0:
        return 'fehler', f'Inhaltsverzeichnis nicht lesbar (Exit {r.returncode})', None
    ok, why, info = check_listing(r.stdout.decode('utf-8', errors='replace'), volumes=len(s.parts))
    if not ok:
        return 'fehler', why, None
    if info['unpacked'] > MAX_RATIO * packed + 100 * 1024**2:
        return 'fehler', f'entpackte Größe unplausibel ({info["unpacked"] // 1024**2} MB aus {packed // 1024**2} MB)', None
    free = shutil.disk_usage(s.directory).free
    if free < info['unpacked'] + RESERVE_BYTES:
        return 'fehler', f'zu wenig Platz ({free // 1024**3} GB frei)', None
    final = s.directory / s.base
    if final.is_dir():                       # früherer Lauf brach nach dem Auspacken ab: nur noch Archive beiseitelegen
        names = {x.name.lower() for x in final.iterdir()}
        if _only_regular_files(final) == info['count'] and all(b in names for b in info['basenames']):
            _stash(s, inbox, today)
            return 'ok', 'war schon ausgepackt, Archive beiseitegelegt', final
        return 'fehler', f'Zielordner {final.name} existiert schon mit anderem Inhalt', None
    if _already_there(s, info['basenames']):
        return 'fehler', 'Dateien liegen schon neben dem Paket (JDownloader war schneller) — nichts getan', None

    tmp = s.directory / (TMP_PREFIX + s.base)
    if tmp.exists():
        shutil.rmtree(tmp)                   # Rest eines abgebrochenen Laufs (nur von uns angelegt)
    tmp.mkdir()
    cmd = []
    if shutil.which('nice'):
        cmd += ['nice', '-n', '19']
    if shutil.which('ionice'):
        cmd += ['ionice', '-c3']
    cmd += [unrar, 'e', '-ai', '-p-', '-o-', '-idq', str(s.first), str(tmp) + os.sep]
    try:
        r = run(cmd, 6 * 3600)
    except subprocess.TimeoutExpired:
        shutil.rmtree(tmp, ignore_errors=True)
        return 'fehler', 'Auspacken dauerte zu lange (Abbruch)', None
    got = _only_regular_files(tmp)
    if got is None:
        shutil.rmtree(tmp, ignore_errors=True)
        return 'fehler', 'Auspacken lieferte etwas anderes als normale Dateien — verworfen', None
    if r.returncode != 0 or got != info['count']:
        shutil.rmtree(tmp, ignore_errors=True)
        return 'fehler', f'Auspacken fehlgeschlagen (Exit {r.returncode}, {got} von {info["count"]} Dateien)', None

    os.replace(tmp, final)
    _stash(s, inbox, today)
    return 'ok', f'{info["count"]} Datei(en) ausgepackt', final


# ── Fehlschläge merken ────────────────────────────────────────────────────────

def _failed_path(inbox: Path) -> Path:
    return inbox / '_Reste' / FAILED_FILE


def load_failed(inbox: Path) -> dict:
    try:
        return json.loads(_failed_path(inbox).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def save_failed(inbox: Path, data: dict):
    p = _failed_path(inbox)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')
    os.replace(tmp, p)


def unpack_all(inbox: Path, apply: bool, min_age: int, max_sets: int = 1, unrar: str = 'unrar', run=_runner):
    """Alle bereiten Pakete (höchstens max_sets pro Lauf). Probelauf: nur anzeigen. -> Statistik-Dict."""
    stats = {'ausgepackt': 0, 'bereit': 0, 'wartet': 0, 'fehler': 0}
    failed = load_failed(inbox)
    done = 0
    for s in find_sets(inbox):
        ready, why = set_ready(s, min_age)
        if not ready:
            print(f'[wartet] Archiv {s.base}: {why}')
            stats['wartet'] += 1
            continue
        key, sig = s.key(inbox), s.signature()
        if failed.get(key, {}).get('signature') == sig:
            print(f'[übersprungen] Archiv {s.base}: scheiterte schon ({failed[key]["grund"]}), unverändert')
            stats['wartet'] += 1
            continue
        if not apply:
            print(f'[Probelauf] würde auspacken: {s.base} ({len(s.parts)} Teil(e))')
            stats['bereit'] += 1
            continue
        if done >= max_sets:
            print(f'[später] Archiv {s.base}: Höchstzahl pro Lauf ({max_sets}) erreicht')
            stats['wartet'] += 1
            continue
        done += 1
        try:
            res, text, _ = unpack_set(s, inbox, unrar=unrar, run=run)
        except Exception as e:   # ein kaputtes Paket darf die anderen nicht stoppen
            res, text = 'fehler', str(e)
        print(f'[{"ausgepackt" if res == "ok" else "Fehler"}] Archiv {s.base}: {text}')
        if res == 'ok':
            stats['ausgepackt'] += 1
            failed.pop(key, None)
        else:
            stats['fehler'] += 1
            failed[key] = {'signature': sig, 'grund': text, 'ts': time.strftime('%Y-%m-%dT%H:%M:%S')}
        try:
            save_failed(inbox, failed)
        except OSError as e:
            print(f'  Fehlerliste nicht gespeichert: {e}')
    return stats
