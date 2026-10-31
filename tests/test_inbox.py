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

    def test_resolution_after_episode_is_not_a_range(self):
        # Wednesday S01: 'S01E01-1080p' wurde fälschlich verworfen (Handover 25.10.)
        for tail in ('-1080p', '_720p', '-2160p', '-480p'):
            r = inbox.parse_episode(f'Wednesday.S01E01{tail}.GERMAN')
            self.assertEqual((r[0], r[1], r[2]), ('Wednesday', 1, [1]), tail)
        self.assertEqual(inbox.parse_episode('Show.S01E01-E02.GERMAN')[2], [1, 2])
        self.assertIsNone(inbox.parse_episode('Show.S01E01-02.GERMAN'))   # echte Bereichsangabe bleibt unklar


class GroupPrefix(unittest.TestCase):
    def test_strip(self):
        r = inbox.parse_episode('jajunge-the.big.bang.theory.s01e01.1080p')
        self.assertEqual(r[0], 'jajunge-the big bang theory')
        self.assertEqual(inbox.strip_group_prefix(r[0]), 'the big bang theory')

    def test_normal_names_untouched(self):
        for n in ('Star Trek - Enterprise', 'Spider-Man', 'The Big Bang Theory', 'Wayward Unberechenbar', ''):
            self.assertIn(inbox.strip_group_prefix(n), ('', 'Man'), n)
        self.assertEqual(inbox.strip_group_prefix('Star Trek - Enterprise'), '')
        self.assertEqual(inbox.strip_group_prefix('The Big Bang Theory'), '')


class FolderNameFallback(unittest.TestCase):
    """Datei 'itn-tbbt.s05e01.1080p.mkv' im Ordner 'The.Big.Bang.Theory.S05E01...' (Big Bang Staffel 5)."""

    class FakeTvdb:
        def search_series(self, q):
            if ' ' not in q:     # TVDb findet 'doctorwho' / 'tbbt' nicht, nur den Namen mit Leerzeichen
                return []
            return [{'name': 'The Big Bang Theory', 'tvdb_id': '80379', 'year': '2007'},
                    {'name': 'Doctor Who', 'tvdb_id': '76107', 'year': '1963'},
                    {'name': 'Doctor Who (2005)', 'tvdb_id': '78804', 'year': '2005'}]

        def episode_info(self, *a):
            return {}

    def _run(self, folder, fname):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            ib = Path(t)
            d = ib / folder
            d.mkdir()
            (ib / 'Serien').mkdir()
            v = d / fname
            v.write_bytes(b'x')
            ctx = {'series_root': ib / 'Serien', 'tvdb': self.FakeTvdb(), 'cache': {}, 'apply': False,
                   'release_dirs': set(), 'min_age': 0}
            stats = {'unklar': 0, 'geplant': 0, 'vorhanden': 0}
            inbox.process_video(v, ctx, stats)
            return stats

    def test_folder_name_resolves(self):
        s = self._run('The.Big.Bang.Theory.S05E01.Der.Schlampen.Reflex.German.DL.1080p.BluRay.x264-iNTENTiON',
                      'itn-tbbt.s05e01.1080p.mkv')
        self.assertEqual((s['geplant'], s['unklar']), (1, 0))

    def test_doctor_who_group_prefix_and_year(self):
        # 'tv4a-doctorwho.2005.s02e01': 'doctorwho' ohne Leerzeichen -> kein Treffer, Ordner 'Doctor.Who.2005.S02E01' mit Jahr -> eindeutig
        s = self._run('Doctor.Who.2005.S02E01.Die.neue.Erde.German.DL.720p.BluRay.x264-TV4A',
                      'tv4a-doctorwho.2005.s02e01-720p.real.mkv')
        self.assertEqual((s['geplant'], s['unklar']), (1, 0))

    def test_year_from_package_folder(self):
        # EXCiTED-Pack: Folge ohne Jahr, nur der Paketordner darüber nennt 2005
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            ib = Path(t)
            d = ib / 'Doctor Who 2005 S01 - S13 Complete German DL 720p BluRay x264-MIX' / 'Doctor.Who.S11E01.German.DL.720p.BluRay.x264-EXCiTED'
            d.mkdir(parents=True)
            (ib / 'Serien').mkdir()
            v = d / 'doctor.who.s11e01.german.dl.720p.bluray.x264-excited.mkv'
            v.write_bytes(b'x')
            ctx = {'inbox': ib, 'series_root': ib / 'Serien', 'tvdb': self.FakeTvdb(), 'cache': {}, 'apply': False,
                   'release_dirs': set(), 'min_age': 0}
            stats = {'unklar': 0, 'geplant': 0, 'vorhanden': 0}
            inbox.process_video(v, ctx, stats)
            self.assertEqual((stats['geplant'], stats['unklar']), (1, 0))

    def test_folder_numbering_beats_wrong_file_numbering(self):
        # Christmas-Special: Ordner S02E00, die Gruppe hat die Datei 's02e01' genannt
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            s = self._run('Doctor.Who.2005.S02E00.Die.Weihnachtsinvasion.German.DL.720p.BluRay.x264-TV4A',
                          'tv4a-doctorwho.2005.s02e01-720p.mkv')
        self.assertEqual((s['geplant'], s['unklar']), (1, 0))
        self.assertIn('S02E00', buf.getvalue().split('->')[-1])
        self.assertNotIn('S02E01', buf.getvalue().split('->')[-1])

    def test_folder_with_several_videos_not_trusted(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            ib = Path(t)
            d = ib / 'The.Big.Bang.Theory.S05E02.Titel.German.1080p-X'
            d.mkdir()
            (ib / 'Serien').mkdir()
            (d / 'itn-tbbt.s05e01.1080p.mkv').write_bytes(b'x')
            (d / 'itn-tbbt.s05e03.1080p.mkv').write_bytes(b'x')   # Sammelordner: Ordnername zählt nicht
            ctx = {'series_root': ib / 'Serien', 'tvdb': self.FakeTvdb(), 'cache': {}, 'apply': False,
                   'release_dirs': set(), 'min_age': 0}
            stats = {'unklar': 0, 'geplant': 0, 'vorhanden': 0}
            inbox.process_video(d / 'itn-tbbt.s05e01.1080p.mkv', ctx, stats)
            self.assertEqual((stats['geplant'], stats['unklar']), (0, 1))


class JellyfinRefresh(unittest.TestCase):
    def test_refresh_replaces_metadata_from_nfo(self):
        calls = []

        def fake_jf(url, key, path, method='GET', body=None):
            calls.append((method, path))
            if path.startswith('/Items?Recursive'):
                return {'Items': [{'Id': 'abc', 'Path': '/s/Doctor Who (2005)'}]}
            return None
        orig, inbox._jf = inbox._jf, fake_jf
        try:
            self.assertTrue(inbox.jellyfin_refresh_series('u', 'k', '/s/Doctor Who (2005)', 'Doctor Who (2005)', wait=1))
        finally:
            inbox._jf = orig
        refresh = [c for c in calls if '/Refresh' in c[1]]
        self.assertEqual(len(refresh), 1)
        self.assertIn('ReplaceAllMetadata=true', refresh[0][1])
        self.assertIn('MetadataRefreshMode=FullRefresh', refresh[0][1])
        self.assertIn('ReplaceAllImages=false', refresh[0][1])


class EpisodeInfoMatch(unittest.TestCase):
    def _tvdb(self, eps):
        t = E.TVDb.__new__(E.TVDb)
        t._get = lambda path, **kw: {'data': {'episodes': eps}}
        return t

    def test_episode_zero_does_not_return_first_episode(self):
        # TVDb liefert bei episodeNumber=0 die ganze Staffel -> S02E00 darf nicht den Titel von S02E01 bekommen
        eps = [{'id': 1, 'name': 'Die neue Erde', 'number': 1, 'seasonNumber': 2, 'overview': 'x'}]
        self.assertEqual(self._tvdb(eps).episode_info(78804, 2, 0), {})

    def test_normal_episode(self):
        eps = [{'id': 1, 'name': 'Die neue Erde', 'number': 1, 'seasonNumber': 2, 'overview': 'x'}]
        self.assertEqual(self._tvdb(eps).episode_info(78804, 2, 1)['title'], 'Die neue Erde')

    def test_without_number_fields_old_behaviour(self):
        self.assertEqual(self._tvdb([{'id': 1, 'name': 'A', 'overview': ''}]).episode_info(1, 1, 1)['title'], 'A')


class UnclearReport(unittest.TestCase):
    def test_report_written_and_removed(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            inb = Path(t)
            stats = {'unklar': 0}
            inbox.unklar(stats, inb / 'Film' / 'x.mkv', 'Kein Filmtitel erkennbar')
            self.assertEqual(stats['unklar'], 1)
            f = inbox.write_unclear_report(inb, stats['_liste'], now='2026-10-26 20:00')
            txt = f.read_text(encoding='utf-8')
            self.assertIn('- Film/x.mkv', txt)
            self.assertIn('Kein Filmtitel erkennbar', txt)
            self.assertFalse((inb / '_Unklar.tmp').exists())
            self.assertIsNone(inbox.write_unclear_report(inb, []))     # nichts mehr unklar -> Datei weg
            self.assertFalse(f.exists())
            self.assertIsNone(inbox.write_unclear_report(inb, []))     # und ohne Fehler, wenn es sie nicht gibt


class Trailer(unittest.TestCase):
    PLUGIN = 'plugin://plugin.video.youtube/play/?video_id='

    def test_german_before_english_before_other(self):
        tr = [{'language': 'fra', 'url': 'https://www.youtube.com/watch?v=aaaaaaaaaaa'},
              {'language': 'eng', 'url': 'https://www.youtube.com/watch?v=bbbbbbbbbbb'},
              {'language': 'deu', 'url': 'https://youtu.be/ccccccccccc'}]
        self.assertEqual(E.youtube_trailer_tag(tr), self.PLUGIN + 'ccccccccccc')
        self.assertEqual(E.youtube_trailer_tag(tr[:2]), self.PLUGIN + 'bbbbbbbbbbb')

    def test_only_youtube_and_robust(self):
        self.assertEqual(E.youtube_trailer_tag([{'language': 'deu', 'url': 'https://vimeo.com/123456'}]), '')
        self.assertEqual(E.youtube_trailer_tag([{'url': 'https://www.youtube.com/embed/9briFc-xzdE?x=1'}]),
                         self.PLUGIN + '9briFc-xzdE')
        for bad in (None, [], [None, 'x', {}], [{'url': None}], [{'url': 'https://www.youtube.com/watch?v=zu_kurz'}]):
            self.assertEqual(E.youtube_trailer_tag(bad), '')

    def test_tvshow_nfo_has_trailer_only_when_given(self):
        s = {'name': 'X', 'id': 'series-1'}
        self.assertIn(f'<trailer>{self.PLUGIN}abcdefghijk</trailer>', E.build_tvshow_nfo(s, self.PLUGIN + 'abcdefghijk'))
        self.assertNotIn('<trailer>', E.build_tvshow_nfo(s))


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

    def test_year_hint_path_package_folder(self):
        ib = Path('/in')
        v = ib / 'Doctor Who 2005 S01 - S13 Complete German DL 720p-MIX' / 'Doctor.Who.S11E01.German-EXCiTED' / 'doctor.who.s11e01.mkv'
        self.assertEqual(inbox.year_hint_path(v, ib), 2005)
        v2 = ib / 'Tulsa.King.S01.German.1080p-X' / 'Tulsa.King.S01E01' / 'tulsa.king.s01e01.mkv'
        self.assertIsNone(inbox.year_hint_path(v2, ib))
        v3 = ib / 'Pack 2005 S01-S03' / 'Doctor.Who.2009.S01E01' / 'x.mkv'
        self.assertEqual(inbox.year_hint_path(v3, ib), 2009)   # näher an der Datei gewinnt

    def test_year_hint_and_regex_edges(self):
        self.assertEqual(inbox.year_hint('Doctor.Who.2005.S01E01.German'), 2005)
        self.assertIsNone(inbox.year_hint('Tulsa.King.S01E01.1080p'))
        self.assertIsNone(inbox.parse_episode('Show.S01E01-02.German'))   # unsicher -> bleibt liegen


class Movies(unittest.TestCase):
    class FakeTmdb:
        def __init__(self, results):
            self.results = results
            self.asked = []

        def search_movie(self, title, year=None):
            self.asked.append((title, year))
            return self.results

        def movie_details(self, i):
            return {'id': i, 'title': 'Leon - Der Profi', 'original_title': 'Léon', 'release_date': '1994-09-14',
                    'overview': 'Text', 'genres': []}

        def poster_url(self, d):
            return None

    LEON = {'id': 101, 'title': 'Leon - Der Profi', 'original_title': 'Léon', 'release_date': '1994-09-14'}

    def test_unique(self):
        self.assertEqual(inbox.pick_movie(self.FakeTmdb([self.LEON]), 'Leon Der Profi', '1994')[0]['id'], 101)

    def test_original_title_matches(self):
        self.assertEqual(inbox.pick_movie(self.FakeTmdb([self.LEON]), 'Leon', '1994')[0]['id'], 101)

    def test_no_year_is_unsure(self):
        self.assertIsNone(inbox.pick_movie(self.FakeTmdb([self.LEON]), 'Leon Der Profi', '')[0])

    def test_wrong_year_is_unsure(self):
        self.assertIsNone(inbox.pick_movie(self.FakeTmdb([self.LEON]), 'Leon Der Profi', '1995')[0])

    def test_remake_two_hits_same_year_unsure(self):
        r = [self.LEON, dict(self.LEON, id=102)]
        self.assertIsNone(inbox.pick_movie(self.FakeTmdb(r), 'Leon Der Profi', '1994')[0])

    def test_different_title_unsure(self):
        self.assertIsNone(inbox.pick_movie(self.FakeTmdb([dict(self.LEON, title='Anderer', original_title='Other')]),
                                           'Leon Der Profi', '1994')[0])

    def _setup(self, tmdb, with_movies=True, files=None):
        import tempfile
        tmp = Path(tempfile.mkdtemp())
        ib, mv = tmp / 'Eingang', tmp / 'Filme'
        ib.mkdir(); mv.mkdir()
        for f in (files or ['Leon.der.Profi.1994.German.DL.1080p.BluRay.x264-GRP/leon.mkv']):
            p = ib / f
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b'x')
        ctx = {'inbox': ib, 'movies_root': mv if with_movies else None, 'tmdb': tmdb, 'movie_cache': {},
               'apply': True, 'touched_movies': set(), 'release_dirs': set(),
               'log': open(tmp / 'log.jsonl', 'w')}
        stats = {'einsortiert': 0, 'geplant': 0, 'vorhanden': 0, 'unklar': 0}
        return ib, mv, ctx, stats

    def test_moves_movie(self):
        ib, mv, ctx, stats = self._setup(self.FakeTmdb([self.LEON]))
        orig = inbox.MIN_VIDEO_BYTES
        inbox.MIN_VIDEO_BYTES = 1
        try:
            v = next(inbox.find_videos(ib))
            inbox.process_movie(v, ctx, stats)
        finally:
            inbox.MIN_VIDEO_BYTES = orig
        self.assertEqual(stats['einsortiert'], 1)
        self.assertTrue((mv / 'Leon - Der Profi (1994)' / 'Leon - Der Profi (1994).mkv').exists())
        self.assertTrue((mv / 'Leon - Der Profi (1994)' / 'movie.nfo').exists())

    def test_without_dest_movies_stays(self):
        ib, mv, ctx, stats = self._setup(self.FakeTmdb([self.LEON]), with_movies=False)
        v = next(inbox.find_videos(ib))
        inbox.process_movie(v, ctx, stats)
        self.assertEqual(stats['unklar'], 1)
        self.assertTrue(v.exists())

    def test_dry_run_changes_nothing(self):
        ib, mv, ctx, stats = self._setup(self.FakeTmdb([self.LEON]))
        ctx['apply'] = False
        v = next(inbox.find_videos(ib))
        inbox.process_movie(v, ctx, stats)
        self.assertEqual(stats['geplant'], 1)
        self.assertTrue(v.exists())
        self.assertEqual(list(mv.iterdir()), [])

    def test_existing_target_not_overwritten(self):
        ib, mv, ctx, stats = self._setup(self.FakeTmdb([self.LEON]))
        (mv / 'Leon - Der Profi (1994)').mkdir()
        v = next(inbox.find_videos(ib))
        inbox.process_movie(v, ctx, stats)
        self.assertEqual(stats['vorhanden'], 1)
        self.assertTrue(v.exists())

    def test_two_videos_in_folder_stay(self):
        ib, mv, ctx, stats = self._setup(self.FakeTmdb([self.LEON]),
                                         files=['Pack/a.1994.mkv', 'Pack/b.1995.mkv'])
        orig = inbox.MIN_VIDEO_BYTES
        inbox.MIN_VIDEO_BYTES = 1
        try:
            inbox.process_movie(sorted(inbox.find_videos(ib))[0], ctx, stats)
        finally:
            inbox.MIN_VIDEO_BYTES = orig
        self.assertEqual(stats['unklar'], 1)


if __name__ == '__main__':
    unittest.main()
