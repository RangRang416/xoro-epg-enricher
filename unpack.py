#!/usr/bin/env python3
"""
unpack.py — mehrteilige RAR-Archive im Eingangsordner sicher auspacken (#53).

Regeln (die Archive stammen aus fremden Downloads, die NAS hat 1 GB RAM und ein altes unrar 5.70):
  - Nur VOLLSTÄNDIGE Pakete: alle Teile 1..n vorhanden, keine Teil-Downloads (.part/.!ut/...) mit gleichem
    Namensanfang, nichts frisch geändert.
  - Vorher Inhaltsverzeichnis lesen (`unrar lt`): nur normale Dateien/Ordner, keine Verknüpfungen, keine
    absoluten oder '..'-Pfade — sonst wird NICHT ausgepackt (Fail-closed).
  - Ausgepackt wird flach (`unrar e`) in einen Temp-Ordner im Eingang, mit niedriger Priorität; erst bei
    Exit-Code 0 und passender Dateizahl wird er zum Release-Ordner.
  - Archive werden NIE gelöscht, sondern nach _Reste/Archive-<Datum>/ verschoben.
  - Platz: mindestens das Doppelte der Teile muss frei sein.
Nur Python-stdlib.
"""

import datetime
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

TMP_PREFIX = '.entpacken-'
ARCHIVE_DIRNAME = 'Archive'
UNFINISHED_EXTS = {'.part', '.!ut', '.crdownload', '.tmp', '.jdownloader'}
SKIP_DIRS = {'_reste', '@eadir', '#recycle'}

_PART_RE = re.compile(r'^(?P<base>.+)\.part(?P<n>\d+)\.rar$', re.I)
_SOLO_RE = re.compile(r'^(?P<base>.+)\.rar$', re.I)
_NAME_RE = re.compile(r'^\s*Name:\s?(.*)$')
_TYPE_RE = re.compile(r'^\s*Type:\s*(.*?)\s*$')


class ArchiveSet:
    def __init__(self, directory: Path, base: str):
        self.directory, self.base = directory, base
        self.parts = {}          # Teilnummer -> Pfad (Einzel-RAR: Nummer 1)

    @property
    def first(self) -> Path:
        return self.parts[min(self.parts)]

    def paths(self):
        return [self.parts[n] for n in sorted(self.parts)]


def find_sets(inbox: Path):
    """Alle RAR-Pakete im Eingang (rekursiv), ohne _Reste/@eaDir/Temp-Ordner."""
    sets = {}
    for p in sorted(inbox.rglob('*.rar')):
        try:
            rel = p.relative_to(inbox)
            if not p.is_file() or any(x.lower() in SKIP_DIRS or x.startswith(TMP_PREFIX) or x.startswith('@')
                                      for x in rel.parts[:-1]):
                continue
        except (OSError, ValueError):
            continue
        m = _PART_RE.match(p.name)
        if m:
            base, num = m.group('base'), int(m.group('n'))
        else:
            m = _SOLO_RE.match(p.name)
            if not m:
                continue
            base, num = m.group('base'), 1
        s = sets.setdefault((p.parent, base), ArchiveSet(p.parent, base))
        s.parts[num] = p
    return list(sets.values())


def _unfinished_siblings(s: ArchiveSet):
    prefix = s.base.lower() + '.'
    try:
        return [x.name for x in s.directory.iterdir()
                if x.is_file() and x.name.lower().startswith(prefix) and x.suffix.lower() in UNFINISHED_EXTS]
    except OSError:
        return ['(Ordner nicht lesbar)']


def set_ready(s: ArchiveSet, min_age: int, now: float = None):
    """(True, '') oder (False, Grund). Prüft Vollständigkeit, Teil-Downloads und Alter."""
    now = time.time() if now is None else now
    nums = sorted(s.parts)
    if nums != list(range(1, nums[-1] + 1)):
        return False, f'Teile unvollständig (vorhanden: {nums})'
    unfinished = _unfinished_siblings(s)
    if unfinished:
        return False, f'Teil-Download läuft noch ({unfinished[0]})'
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


def check_listing(text: str):
    """Prüft die Ausgabe von `unrar lt`. -> (ok, Grund, Zahl der Dateien). Fail-closed."""
    entries, cur = [], None
    for line in text.splitlines():
        m = _NAME_RE.match(line)
        if m:
            cur = {'name': m.group(1), 'type': None}
            entries.append(cur)
            continue
        m = _TYPE_RE.match(line)
        if m and cur is not None and cur['type'] is None:
            cur['type'] = m.group(1)
    if not entries:
        return False, 'Inhaltsverzeichnis leer/nicht lesbar', 0
    files = 0
    for e in entries:
        name, typ = e['name'], (e['type'] or '').lower()
        if typ not in ('file', 'directory'):
            return False, f'Eintrag mit Typ "{e["type"]}" ({name})', 0
        parts = re.split(r'[\\/]', name)
        if (not name or name.startswith(('/', '\\')) or re.match(r'^[A-Za-z]:', name) or '..' in parts
                or '\\' in name or '\0' in name):
            return False, f'Unzulässiger Pfad im Archiv: {name!r}', 0
        if typ == 'file':
            files += 1
    return True, '', files


def _runner(cmd, timeout):
    return subprocess.run(cmd, capture_output=True, timeout=timeout)


def unpack_set(s: ArchiveSet, inbox: Path, unrar: str = 'unrar', run=_runner, today: str = None):
    """Packt ein bereites Paket aus. -> (Ergebnis 'ok'|'fehler', Text, Release-Ordner|None)."""
    total = 0
    for p in s.paths():
        total += p.stat().st_size
    free = shutil.disk_usage(s.directory).free
    if free < 2 * total:
        return 'fehler', f'zu wenig Platz ({free // 1024**3} GB frei, {2 * total // 1024**3} GB nötig)', None

    r = run([unrar, 'lt', '-p-', '-idq', str(s.first)], 600)
    if r.returncode != 0:
        return 'fehler', f'Inhaltsverzeichnis nicht lesbar (Exit {r.returncode})', None
    ok, why, nfiles = check_listing(r.stdout.decode('utf-8', errors='replace'))
    if not ok:
        return 'fehler', why, None

    tmp = inbox / (TMP_PREFIX + s.base)
    if tmp.exists():
        shutil.rmtree(tmp)          # Rest eines früheren, abgebrochenen Laufs (nur von uns angelegt)
    tmp.mkdir(parents=True)
    cmd = []
    if shutil.which('nice'):
        cmd += ['nice', '-n', '19']
    if shutil.which('ionice'):
        cmd += ['ionice', '-c3']
    cmd += [unrar, 'e', '-p-', '-o-', '-idq', str(s.first), str(tmp) + os.sep]
    try:
        r = run(cmd, 6 * 3600)
    except subprocess.TimeoutExpired:
        shutil.rmtree(tmp, ignore_errors=True)
        return 'fehler', 'Auspacken dauerte zu lange (Abbruch)', None
    got = sum(1 for x in tmp.rglob('*') if x.is_file())
    if r.returncode != 0 or got != nfiles:
        shutil.rmtree(tmp, ignore_errors=True)
        return 'fehler', f'Auspacken fehlgeschlagen (Exit {r.returncode}, {got} von {nfiles} Dateien)', None

    final = inbox / s.base
    n = 2
    while final.exists():
        final = inbox / f'{s.base}_{n}'
        n += 1
    os.replace(tmp, final)
    # Archive nie löschen: beiseitelegen (gleiches Volume -> nur Umbenennen)
    day = today or datetime.date.today().isoformat()
    arch = inbox / '_Reste' / f'{ARCHIVE_DIRNAME}-{day}' / s.base
    arch.mkdir(parents=True, exist_ok=True)
    for p in s.paths():
        shutil.move(str(p), str(arch / p.name))
    return 'ok', f'{nfiles} Datei(en) ausgepackt', final


def unpack_all(inbox: Path, apply: bool, min_age: int, max_sets: int = 3, unrar: str = 'unrar', run=_runner):
    """Alle bereiten Pakete (höchstens max_sets pro Lauf). Probelauf: nur anzeigen. -> Statistik-Dict."""
    stats = {'ausgepackt': 0, 'bereit': 0, 'wartet': 0, 'fehler': 0}
    done = 0
    for s in find_sets(inbox):
        ready, why = set_ready(s, min_age)
        if not ready:
            print(f'[wartet] Archiv {s.base}: {why}')
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
        stats['ausgepackt' if res == 'ok' else 'fehler'] += 1
    return stats
