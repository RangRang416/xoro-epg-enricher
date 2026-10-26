import os, sys, tempfile, time, unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import unpack


def listing(entries, volumes=2, extra=''):
    """Nachbau der `unrar lt -v`-Ausgabe: je Volume ein 'Archive:'-Block; Einträge als (Name, Typ, Größe)."""
    out = []
    for v in range(1, volumes + 1):
        out.append(f'Archive: x.part{v}.rar\nDetails: RAR 5\n')
        if v == 1:
            for name, typ, size in entries:
                out.append(f'        Name: {name}\n        Type: {typ}\n        Size: {size}\n'
                           f' Packed size: {size}\n       Ratio: 100%\n Compression: RAR 5.0(v50) -m0 -md=128M\n{extra}\n')
    return ''.join(out)


GOOD = [('Monk.S07E04.German/fkktv-monk.s07e04-1080p.mkv', 'File', 150), ('Monk.S07E04.German', 'Directory', 0)]


def touch(p: Path, size=10, age=10_000):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b'x' * size)
    t = time.time() - age
    os.utime(p, (t, t))
    return p


class Listing(unittest.TestCase):
    def test_ok(self):
        ok, _, info = unpack.check_listing(listing(GOOD), volumes=2)
        self.assertTrue(ok)
        self.assertEqual((info['count'], info['unpacked']), (1, 150))

    def test_volume_count_must_match(self):
        self.assertFalse(unpack.check_listing(listing(GOOD, volumes=1), volumes=2)[0])   # nur Teil 1 gelistet
        self.assertFalse(unpack.check_listing('Name: a\nType: File\nSize: 1\n', volumes=1)[0])

    def test_link_types_and_target_rejected(self):
        for typ in ('Unix symbolic link', 'Windows symbolic link', 'Hard link', 'File copy', 'Symlink'):
            self.assertFalse(unpack.check_listing(listing([('a.mkv', 'File', 1), ('b', typ, 0)]), 2)[0], typ)
        self.assertFalse(unpack.check_listing(listing(GOOD, extra='      Target: ..\\..\\x'), 2)[0])

    def test_line_break_in_name_cannot_forge_type(self):
        # \x0b, \r, \x85, U+2028 trennt str.splitlines() — hier darf es keinen zweiten Type einschleusen
        for sep in ('\x0b', '\x0c', '\x1c', '\x85', '\u2028', '\u2029', '\r'):
            text = listing([(f'a{sep}        Type: File', 'Unix symbolic link', 0)], 2)
            self.assertFalse(unpack.check_listing(text, 2)[0], repr(sep))
        text = 'Archive: x\nArchive: y\n        Name: a\n        Type: File\n        Type: Unix symbolic link\n        Size: 1\n'
        self.assertFalse(unpack.check_listing(text, 2)[0])      # doppelter Type
        self.assertFalse(unpack.check_listing('Archive: x\n        Type: File\n        Name: a\n', 1)[0])  # Type vor Name

    def test_path_tricks_rejected(self):
        for bad in ('../x.mkv', 'a/../../x.mkv', '/etc/x.mkv', 'C:\\x.mkv', 'a\\b.mkv', 'a\x07b.mkv'):
            self.assertFalse(unpack.check_listing(listing([(bad, 'File', 1)], 1), 1)[0], repr(bad))

    def test_duplicate_basenames_rejected_but_split_files_ok(self):
        dup = [('a/x.mkv', 'File', 1), ('b/X.mkv', 'File', 1)]
        self.assertFalse(unpack.check_listing(listing(dup, 2), 2)[0])
        # dieselbe Datei in mehreren Volumes (geteilt) darf nur einmal zählen
        text = ('Archive: a\n  Name: v.mkv\n  Type: File\n  Size: 100\nArchive: b\n  Name: v.mkv\n  Type: File\n  Size: 100\n')
        ok, _, info = unpack.check_listing(text, 2)
        self.assertTrue(ok)
        self.assertEqual((info['count'], info['unpacked']), (1, 100))

    def test_empty_or_sizeless_fails_closed(self):
        self.assertFalse(unpack.check_listing('')[0])
        self.assertFalse(unpack.check_listing('Name: a.mkv\nType: File\n')[0])


class Sets(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.inbox = Path(self._t.name)

    def tearDown(self):
        self._t.cleanup()

    def mk(self, names, **kw):
        for n in names:
            touch(self.inbox / n, **kw)

    def test_complete_set_ready(self):
        self.mk(['108BD-Show-S01E01.part1.rar', '108BD-Show-S01E01.part2.rar'])
        (s,) = unpack.find_sets(self.inbox)
        self.assertEqual(unpack.set_ready(s, 300), (True, ''))

    def test_gap_in_parts_not_ready(self):
        self.mk(['a.part1.rar', 'a.part3.rar'])
        (s,) = unpack.find_sets(self.inbox)
        self.assertFalse(unpack.set_ready(s, 300)[0])

    def test_unfinished_sibling_blocks(self):
        self.mk(['a.part1.rar', 'a.part2.rar.part'])
        (s,) = unpack.find_sets(self.inbox)
        ready, why = unpack.set_ready(s, 300)
        self.assertFalse(ready)
        self.assertIn('Teil-Download', why)

    def test_fresh_part_blocks(self):
        self.mk(['a.part1.rar'])
        touch(self.inbox / 'a.part2.rar', age=5)
        (s,) = unpack.find_sets(self.inbox)
        self.assertFalse(unpack.set_ready(s, 300)[0])

    def test_uppercase_extension_found_and_old_style_refused(self):
        self.mk(['a.part1.RAR', 'a.part2.rar'])
        (s,) = unpack.find_sets(self.inbox)
        self.assertEqual(sorted(s.parts), [1, 2])
        self.mk(['b.rar', 'b.r00'])
        sets = {x.base: x for x in unpack.find_sets(self.inbox)}
        self.assertIn('alte RAR-Benennung', unpack.set_ready(sets['b'], 300)[1])

    def test_other_sets_do_not_block_each_other(self):
        self.mk(['a.part1.rar', 'a.part2.rar', 'b.part1.rar.part'])
        sets = {s.base: s for s in unpack.find_sets(self.inbox)}
        self.assertEqual(list(sets), ['a'])
        self.assertTrue(unpack.set_ready(sets['a'], 300)[0])

    def test_reste_and_tmp_skipped(self):
        self.mk(['_Reste/x/a.part1.rar', '.entpacken-b/b.rar', '@eaDir/c.rar'])
        self.assertEqual(unpack.find_sets(self.inbox), [])


class Unpack(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.inbox = Path(self._t.name)
        self._reserve, unpack.RESERVE_BYTES = unpack.RESERVE_BYTES, 0
        self.put_set('show')
        self.calls = []

    def tearDown(self):
        unpack.RESERVE_BYTES = self._reserve
        self._t.cleanup()

    def put_set(self, base, where=None, size=100):
        d = where or self.inbox
        touch(d / f'{base}.part1.rar', size=size)
        touch(d / f'{base}.part2.rar', size=size)

    def sets(self):
        return {s.base: s for s in unpack.find_sets(self.inbox)}

    def runner(self, entries=GOOD, rc_ext=0, make=None, volumes=2):
        def run(cmd, timeout):
            self.calls.append(cmd)
            if 'lt' in cmd:
                self.assertIn('-v', cmd)
                self.assertNotIn('-idq', cmd)       # sonst wäre das Verzeichnis leer
                return SimpleNamespace(returncode=0, stdout=listing(entries, volumes).encode(), stderr=b'')
            out = Path(cmd[-1])
            (make or (lambda o: (o / 'f.mkv').write_bytes(b'v')))(out)
            return SimpleNamespace(returncode=rc_ext, stdout=b'', stderr=b'')
        return run

    def test_success_moves_archives_aside_never_deletes(self):
        res, _, final = unpack.unpack_set(self.sets()['show'], self.inbox, run=self.runner(), today='2026-10-26')
        self.assertEqual(res, 'ok')
        self.assertEqual(final, self.inbox / 'show')
        self.assertFalse((self.inbox / '.entpacken-show').exists())
        kept = self.inbox / '_Reste' / 'Archive-2026-10-26' / 'show'
        self.assertEqual(sorted(p.name for p in kept.iterdir()), ['show.part1.rar', 'show.part2.rar'])
        ext = next(c for c in self.calls if 'e' in c and 'lt' not in c)
        self.assertIn('-ai', ext)

    def test_archives_never_overwritten(self):
        arch = self.inbox / '_Reste' / 'Archive-2026-10-26'
        (arch / 'show').mkdir(parents=True)
        (arch / 'show' / 'show.part1.rar').write_bytes(b'ALT')
        res, _, _ = unpack.unpack_set(self.sets()['show'], self.inbox, run=self.runner(), today='2026-10-26')
        self.assertEqual(res, 'ok')
        self.assertEqual((arch / 'show' / 'show.part1.rar').read_bytes(), b'ALT')
        self.assertTrue((arch / 'show_2' / 'show.part1.rar').exists())

    def test_nothing_extracted_when_listing_bad(self):
        bad = [('a.mkv', 'File', 1), ('b', 'Unix symbolic link', 0)]
        res, _, _ = unpack.unpack_set(self.sets()['show'], self.inbox, run=self.runner(entries=bad))
        self.assertEqual(res, 'fehler')
        self.assertEqual(len(self.calls), 1)
        self.assertTrue((self.inbox / 'show.part1.rar').exists())

    def test_only_part1_listed_is_refused(self):
        res, why, _ = unpack.unpack_set(self.sets()['show'], self.inbox, run=self.runner(volumes=1))
        self.assertEqual(res, 'fehler')
        self.assertIn('Volumes', why)
        self.assertEqual(len(self.calls), 1)

    def test_symlink_created_by_extraction_is_caught(self):
        def make(out):
            (out / 'f.mkv').write_bytes(b'v')
            os.symlink('/etc/passwd', out / 'evil')
        res, why, _ = unpack.unpack_set(self.sets()['show'], self.inbox, run=self.runner(make=make))
        self.assertEqual(res, 'fehler')
        self.assertFalse((self.inbox / '.entpacken-show').exists())
        self.assertTrue((self.inbox / 'show.part1.rar').exists())

    def test_failed_extraction_keeps_everything(self):
        res, _, _ = unpack.unpack_set(self.sets()['show'], self.inbox, run=self.runner(rc_ext=3))
        self.assertEqual(res, 'fehler')
        self.assertTrue((self.inbox / 'show.part1.rar').exists())
        self.assertFalse((self.inbox / '.entpacken-show').exists() or (self.inbox / 'show').exists())

    def test_file_count_mismatch_is_failure(self):
        res, _, _ = unpack.unpack_set(self.sets()['show'], self.inbox, run=self.runner(make=lambda o: None))
        self.assertEqual(res, 'fehler')

    def test_decompression_bomb_refused(self):
        huge = [('a.mkv', 'File', 50 * 1024**3)]
        res, why, _ = unpack.unpack_set(self.sets()['show'], self.inbox, run=self.runner(entries=huge))
        self.assertEqual(res, 'fehler')
        self.assertIn('unplausibel', why)
        self.assertEqual(len(self.calls), 1)

    def test_not_enough_space_refused(self):
        unpack.RESERVE_BYTES = 10**18
        res, why, _ = unpack.unpack_set(self.sets()['show'], self.inbox, run=self.runner())
        self.assertEqual((res, 'Platz' in why), ('fehler', True))

    def test_jdownloader_was_faster(self):
        touch(self.inbox / 'Monk.S07E04.German' / 'fkktv-monk.s07e04-1080p.mkv', size=5)
        res, why, _ = unpack.unpack_set(self.sets()['show'], self.inbox, run=self.runner())
        self.assertEqual(res, 'fehler')
        self.assertIn('JDownloader', why)
        self.assertEqual(len(self.calls), 1)

    def test_resume_after_abort_only_stashes_archives(self):
        (self.inbox / 'show').mkdir()
        (self.inbox / 'show' / 'f.mkv').write_bytes(b'v')
        entries = [('f.mkv', 'File', 1)]
        res, text, _ = unpack.unpack_set(self.sets()['show'], self.inbox, run=self.runner(entries=entries), today='2026-10-26')
        self.assertEqual(res, 'ok')
        self.assertIn('beiseitegelegt', text)
        self.assertEqual(len([c for c in self.calls if 'lt' not in c]), 0)   # nicht erneut ausgepackt

    def test_release_dir_next_to_package(self):
        sub = self.inbox / 'Gruppe'
        self.put_set('deep', where=sub)
        res, _, final = unpack.unpack_set(self.sets()['deep'], self.inbox, run=self.runner())
        self.assertEqual((res, final), ('ok', sub / 'deep'))

    def test_probelauf_changes_nothing(self):
        stats = unpack.unpack_all(self.inbox, apply=False, min_age=300, run=self.runner())
        self.assertEqual((stats['bereit'], stats['ausgepackt']), (1, 0))
        self.assertEqual(self.calls, [])

    def test_max_sets_per_run(self):
        self.put_set('two')
        stats = unpack.unpack_all(self.inbox, apply=True, min_age=300, max_sets=1, run=self.runner())
        self.assertEqual((stats['ausgepackt'], stats['wartet']), (1, 1))

    def test_failure_remembered_until_package_changes(self):
        bad = self.runner(entries=[('a', 'Unix symbolic link', 0)])
        unpack.unpack_all(self.inbox, apply=True, min_age=300, run=bad)
        n = len(self.calls)
        stats = unpack.unpack_all(self.inbox, apply=True, min_age=300, run=bad)
        self.assertEqual(len(self.calls), n)               # unverändert -> nicht noch einmal versucht
        self.assertEqual(stats['fehler'], 0)
        touch(self.inbox / 'show.part2.rar', size=120)      # Paket hat sich geändert -> neuer Versuch
        unpack.unpack_all(self.inbox, apply=True, min_age=300, run=bad)
        self.assertGreater(len(self.calls), n)


if __name__ == '__main__':
    unittest.main()
