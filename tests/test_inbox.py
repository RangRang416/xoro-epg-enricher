import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import inbox, enricher as E


class ParseEpisode(unittest.TestCase):
    def test_tulsa(self):
        self.assertEqual(inbox.parse_episode('Tulsa.King.S01E03.Willkuer.GERMAN.DUBBED.DL.1080p.BDRiP.x264-TSCC'),
                         ('Tulsa King', 1, [3], 'S01E03'))

    def test_electric_dreams(self):
        r = inbox.parse_episode('Philip.K.Dicks.Electric.Dreams.S01E03.Menschlich.ist.German.DD+51.DL.1080p')
        self.assertEqual(r[0], 'Philip K Dicks Electric Dreams')
        self.assertEqual(r[1:3], (1, [3]))

    def test_double_episode(self):
        r = inbox.parse_episode('Star.Trek.TNG.S01E01E02.Der.Maechtige.Mission.Farpoint.REPACK')
        self.assertEqual((r[0], r[1], r[2]), ('Star Trek TNG', 1, [1, 2]))

    def test_lowercase_and_year(self):
        r = inbox.parse_episode('wayward.unberechenbar.s01e07.german.dl.1080p.web.h264-sauerkraut')
        self.assertEqual((r[0], r[1], r[2]), ('wayward unberechenbar', 1, [7]))
        self.assertEqual(inbox.parse_episode('Dalgliesh.2021.S02E01.German')[0], 'Dalgliesh')

    def test_no_match_cryptic(self):
        self.assertIsNone(inbox.parse_episode('tvs-sttng-dd20-dl-18p-bd-x264-103'))
        self.assertIsNone(inbox.parse_episode('Leon.der.Profi.1994.German.DL.1080p.BluRay.x264'))

    def test_codec_not_episode(self):
        # "x264" / "1080p" dürfen nicht als Folge gelesen werden
        self.assertIsNone(inbox.parse_episode('Some.Movie.2020.German.1080p.x264-GRP'))

    def test_two_digit_episode_not_cut(self):
        self.assertEqual(inbox.parse_episode('Show.S02E12.Titel')[2], [12])
        self.assertEqual(inbox.parse_episode('Show.S10E105.Titel')[2], [105])


class Helpers(unittest.TestCase):
    def test_tvdb_id_prefix(self):
        self.assertEqual(E._tvdb_id({'id': 'series-413215', 'tvdb_id': '413215'}), 413215)
        self.assertEqual(E._tvdb_id({'id': 'series-413215'}), 413215)
        self.assertEqual(E._tvdb_id({'id': 75299}), 75299)
        self.assertEqual(E._tvdb_id({}), '')

    def test_episode_nfo_no_series_overview(self):
        nfo = E.build_episode_nfo({'name': 'X', 'overview': 'SERIENTEXT', 'tvdb_id': '5'}, 1, 2)
        self.assertNotIn('SERIENTEXT', nfo)
        self.assertIn('<uniqueid>5</uniqueid>', nfo)

    def test_norm_name(self):
        self.assertEqual(E._norm_name("Philip K. Dick's Electric Dreams"), E._norm_name('Philip K Dicks Electric Dreams'))

    def test_sanitize(self):
        self.assertEqual(inbox.sanitize('Titel: Der "Test"?'), 'Titel Der Test')


class Cleanup(unittest.TestCase):
    """Das Aufräumen darf NIE Videos, Archive oder Frisches wegräumen (Review #53)."""

    def _mk(self, files):
        import tempfile
        self.tmp = Path(tempfile.mkdtemp())
        inbox = self.tmp / 'Eingang'
        for f in files:
            p = inbox / f
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('x')
        return inbox

    def _run(self, inbox, dirs, min_age=0):
        ctx = {'release_dirs': set(dirs), 'min_age': min_age}
        inbox_mod = inbox
        inbox_mod_ = inbox  # noqa
        import inbox as m
        m.cleanup_release_dirs(ctx, inbox_mod)

    def test_junk_only_moved_and_dir_removed(self):
        i = self._mk(['Grp/Rel1/scene.nfo', 'Grp/Rel1/Sample/s.mkv'])
        self._run(i, [i / 'Grp/Rel1'])
        self.assertTrue((i / '_Reste/Rel1/scene.nfo').exists())
        self.assertFalse((i / 'Grp').exists())          # leerer Gruppenordner ist weg

    def test_sibling_video_blocks_cleanup(self):
        i = self._mk(['Pack/E01.nfo', 'Pack/E05.mkv', 'Pack/E06.part1.rar'])
        self._run(i, [i / 'Pack'])
        self.assertTrue((i / 'Pack/E05.mkv').exists())
        self.assertTrue((i / 'Pack/E06.part1.rar').exists())
        self.assertFalse((i / '_Reste').exists())

    def test_existing_target_not_overwritten(self):
        i = self._mk(['A/Rel/scene.nfo', '_Reste/Rel/scene.nfo'])
        (i / '_Reste/Rel/scene.nfo').write_text('ALT')
        self._run(i, [i / 'A/Rel'])
        self.assertEqual((i / '_Reste/Rel/scene.nfo').read_text(), 'ALT')
        self.assertTrue((i / '_Reste/Rel_2/scene.nfo').exists())

    def test_fresh_files_untouched(self):
        i = self._mk(['Rel/scene.nfo'])
        self._run(i, [i / 'Rel'], min_age=3600)
        self.assertTrue((i / 'Rel/scene.nfo').exists())

    def test_nonempty_eadir_not_deleted(self):
        i = self._mk(['Rel/scene.nfo', 'Rel/@eaDir/wichtig.txt'])
        self._run(i, [i / 'Rel'])
        self.assertTrue((i / '_Reste/Rel/scene.nfo').exists())
        self.assertTrue((i / 'Rel/@eaDir/wichtig.txt').exists())   # Inhalt von @eaDir bleibt


class PickSeries(unittest.TestCase):
    class FakeTvdb:
        def __init__(self, results):
            self.results = results

        def search_series(self, q):
            return self.results

    def test_unique(self):
        r = [{'name': 'Tulsa King', 'tvdb_id': '413215', 'year': '2022'}]
        self.assertEqual(inbox.pick_series(self.FakeTvdb(r), 'Tulsa King')[0]['tvdb_id'], '413215')

    def test_remake_ambiguous_without_year(self):
        r = [{'name': 'Doctor Who', 'year': '1963'}, {'name': 'Doctor Who (2005)', 'year': '2005'}]
        self.assertIsNone(inbox.pick_series(self.FakeTvdb(r), 'Doctor Who')[0])

    def test_remake_year_decides(self):
        r = [{'name': 'Doctor Who', 'year': '1963'}, {'name': 'Doctor Who (2005)', 'year': '2005'}]
        self.assertEqual(inbox.pick_series(self.FakeTvdb(r), 'Doctor Who', 2005)[0]['year'], '2005')

    def test_short_name_with_remake_is_unsure(self):
        r = [{'name': 'Electric Dreams', 'year': '2009'},
             {'name': 'Electric Dreams (2017)', 'year': '2017', 'translations': {'deu': "Philip K. Dick's Electric Dreams"}}]
        self.assertIsNone(inbox.pick_series(self.FakeTvdb(r), 'Electric Dreams')[0])

    def test_full_name_via_german_title(self):
        r = [{'name': 'Electric Dreams (2017)', 'year': '2017', 'tvdb_id': '329083',
              'translations': {'deu': "Philip K. Dick's Electric Dreams"}}]
        self.assertEqual(inbox.pick_series(self.FakeTvdb(r), 'Philip K Dicks Electric Dreams')[0]['tvdb_id'], '329083')

    def test_year_hint_and_regex_edges(self):
        self.assertEqual(inbox.year_hint('Doctor.Who.2005.S01E01.German'), 2005)
        self.assertIsNone(inbox.year_hint('Tulsa.King.S01E01.1080p'))
        self.assertIsNone(inbox.parse_episode('Show.S01E01-02.German'))   # unsicher -> bleibt liegen


if __name__ == '__main__':
    unittest.main()
