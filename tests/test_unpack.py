import os, sys, tempfile, time, unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import unpack

LISTING_OK = """
        Name: Monk.S07E04.German.1080p.WebHD.h264-FKKTV/fkktv-monk.s07e04-1080p.mkv
        Type: File
        Size: 1234
        Name: Monk.S07E04.German.1080p.WebHD.h264-FKKTV
        Type: Directory
"""


def touch(p: Path, size=10, age=10_000):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b'x' * size)
    t = time.time() - age
    os.utime(p, (t, t))
    return p


class Listing(unittest.TestCase):
    def test_ok(self):
        self.assertEqual(unpack.check_listing(LISTING_OK), (True, '', 1))

    def test_symlink_rejected(self):
        ok, why, _ = unpack.check_listing('Name: a.mkv\nType: File\nName: b\nType: Unix symbolic link\n')
        self.assertFalse(ok)
        self.assertIn('symbolic', why)

    def test_path_tricks_rejected(self):
        for bad in ('../x.mkv', 'a/../../x.mkv', '/etc/x.mkv', 'C:\\x.mkv', 'a\\b.mkv'):
            self.assertFalse(unpack.check_listing(f'Name: {bad}\nType: File\n')[0], bad)

    def test_empty_or_typeless_fails_closed(self):
        self.assertFalse(unpack.check_listing('')[0])
        self.assertFalse(unpack.check_listing('Name: a.mkv\n')[0])


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

    def test_other_sets_do_not_block_each_other(self):
        self.mk(['a.part1.rar', 'a.part2.rar', 'b.part1.rar.part'])
        sets = {s.base: s for s in unpack.find_sets(self.inbox)}
        self.assertEqual(list(sets), ['a'])   # 'b.part1.rar.part' ist kein .rar -> kein Paket
        self.assertTrue(unpack.set_ready(sets['a'], 300)[0])

    def test_reste_and_tmp_skipped(self):
        self.mk(['_Reste/x/a.part1.rar', '.entpacken-b/b.rar', '@eaDir/c.rar'])
        self.assertEqual(unpack.find_sets(self.inbox), [])


class Unpack(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.inbox = Path(self._t.name)
        touch(self.inbox / 'show.part1.rar', size=100)
        touch(self.inbox / 'show.part2.rar', size=100)
        (self.s,) = unpack.find_sets(self.inbox)
        self.calls = []

    def tearDown(self):
        self._t.cleanup()

    def runner(self, listing=LISTING_OK, rc_list=0, rc_ext=0, make_files=1):
        def run(cmd, timeout):
            self.calls.append(cmd)
            if 'lt' in cmd:
                return SimpleNamespace(returncode=rc_list, stdout=listing.encode(), stderr=b'')
            out = Path(cmd[-1])
            for i in range(make_files):
                (out / f'f{i}.mkv').write_bytes(b'v')
            return SimpleNamespace(returncode=rc_ext, stdout=b'', stderr=b'')
        return run

    def test_success_moves_archives_aside_never_deletes(self):
        res, _, final = unpack.unpack_set(self.s, self.inbox, run=self.runner(), today='2026-10-26')
        self.assertEqual(res, 'ok')
        self.assertEqual(final, self.inbox / 'show')
        self.assertTrue((final / 'f0.mkv').is_file())
        self.assertFalse((self.inbox / '.entpacken-show').exists())
        kept = self.inbox / '_Reste' / 'Archive-2026-10-26' / 'show'
        self.assertEqual(sorted(p.name for p in kept.iterdir()), ['show.part1.rar', 'show.part2.rar'])
        self.assertFalse((self.inbox / 'show.part1.rar').exists())

    def test_extract_only_after_listing_ok(self):
        res, why, _ = unpack.unpack_set(self.s, self.inbox, run=self.runner(listing='Name: a\nType: Symlink\n'))
        self.assertEqual(res, 'fehler')
        self.assertEqual(len(self.calls), 1)      # nur gelistet, nie ausgepackt
        self.assertTrue((self.inbox / 'show.part1.rar').exists())

    def test_failed_extraction_keeps_everything(self):
        res, _, _ = unpack.unpack_set(self.s, self.inbox, run=self.runner(rc_ext=3))
        self.assertEqual(res, 'fehler')
        self.assertTrue((self.inbox / 'show.part1.rar').exists())
        self.assertFalse((self.inbox / '.entpacken-show').exists())
        self.assertFalse((self.inbox / 'show').exists())

    def test_file_count_mismatch_is_failure(self):
        res, _, _ = unpack.unpack_set(self.s, self.inbox, run=self.runner(make_files=0))
        self.assertEqual(res, 'fehler')
        self.assertTrue((self.inbox / 'show.part2.rar').exists())

    def test_existing_release_dir_not_overwritten(self):
        (self.inbox / 'show').mkdir()
        res, _, final = unpack.unpack_set(self.s, self.inbox, run=self.runner())
        self.assertEqual((res, final.name), ('ok', 'show_2'))

    def test_probelauf_changes_nothing(self):
        stats = unpack.unpack_all(self.inbox, apply=False, min_age=300, run=self.runner())
        self.assertEqual((stats['bereit'], stats['ausgepackt']), (1, 0))
        self.assertEqual(self.calls, [])
        self.assertTrue((self.inbox / 'show.part1.rar').exists())

    def test_max_sets_per_run(self):
        touch(self.inbox / 'two.part1.rar', size=100)
        stats = unpack.unpack_all(self.inbox, apply=True, min_age=300, max_sets=1, run=self.runner())
        self.assertEqual((stats['ausgepackt'], stats['wartet']), (1, 1))


if __name__ == '__main__':
    unittest.main()
