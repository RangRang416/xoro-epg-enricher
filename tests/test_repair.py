import sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import repair_episode_nfos as R, enricher as E


def nfo(title, season=1, ep=1, plot='Serientext', show='Wednesday', uid='series-397060'):
    return (f'<?xml version="1.0" ?><episodedetails><title>{title}</title><showtitle>{show}</showtitle>'
            f'<season>{season}</season><episode>{ep}</episode><plot>{plot}</plot><uniqueid>{uid}</uniqueid></episodedetails>')


class Repair(unittest.TestCase):
    def _show(self):
        d = Path(tempfile.mkdtemp()) / 'Wednesday'
        (d / 'S01').mkdir(parents=True)
        (d / 'tvshow.nfo').write_text('<tvshow><title>Wednesday</title><uniqueid type="tvdb" default="true">397060</uniqueid></tvshow>')
        (d / 'S01' / 'a.nfo').write_text(nfo('Wednesday', 1, 1))
        (d / 'S01' / 'b.nfo').write_text(nfo('Eigener Titel', 1, 2))
        return d

    @staticmethod
    def fake(tvdb, i, s, e):
        return {'title': f'Folge {e}', 'overview': f'Text {e}', 'de': True}

    def _run(self, d, apply, backup=None, fn=None):
        stats = {k: 0 for k in ('geplant', 'repariert', 'deutsch', 'englisch', 'in_ordnung', 'unklar', 'nicht_gefunden', 'fehler', 'serie_ohne_id')}
        R.repair_show(d, None, apply, backup, stats, text_fn=fn or self.fake, pause=0)
        return stats

    def test_needs_repair(self):
        self.assertTrue(R.needs_repair({'title': 'Wednesday', 'showtitle': 'Wednesday'}))
        self.assertTrue(R.needs_repair({'title': '', 'showtitle': 'X'}))
        self.assertFalse(R.needs_repair({'title': 'Mittwochskind', 'showtitle': 'Wednesday'}))

    def test_show_info_strips_series_prefix(self):
        d = self._show()
        (d / 'tvshow.nfo').write_text('<tvshow><title>W</title><uniqueid>series-397060</uniqueid></tvshow>')
        self.assertEqual(R.show_info(d)[0], 397060)

    def test_dry_run_changes_nothing(self):
        d = self._show()
        before = (d / 'S01' / 'a.nfo').read_text()
        st = self._run(d, False)
        self.assertEqual((st['geplant'], st['in_ordnung']), (1, 1))
        self.assertEqual((d / 'S01' / 'a.nfo').read_text(), before)

    def test_apply_rewrites_only_bad_and_backs_up(self):
        d = self._show()
        bk = Path(tempfile.mkdtemp())
        keep = (d / 'S01' / 'b.nfo').read_text()
        st = self._run(d, True, bk)
        self.assertEqual(st['repariert'], 1)
        new = (d / 'S01' / 'a.nfo').read_text()
        self.assertIn('<title>Folge 1</title>', new)
        self.assertIn('<plot>Text 1</plot>', new)
        self.assertIn('<uniqueid>397060</uniqueid>', new)       # ohne 'series-'-Vorsatz
        self.assertEqual((d / 'S01' / 'b.nfo').read_text(), keep)
        self.assertIn('<title>Wednesday</title>', (bk / 'Wednesday' / 'S01' / 'a.nfo').read_text())

    def test_not_found_leaves_file(self):
        d = self._show()
        before = (d / 'S01' / 'a.nfo').read_text()
        st = self._run(d, True, Path(tempfile.mkdtemp()), fn=lambda *a: {})
        self.assertEqual(st['nicht_gefunden'], 1)
        self.assertEqual((d / 'S01' / 'a.nfo').read_text(), before)

    def test_tvdb_error_leaves_file(self):
        d = self._show()
        before = (d / 'S01' / 'a.nfo').read_text()
        def boom(*a): raise OSError('x')
        st = self._run(d, True, Path(tempfile.mkdtemp()), fn=boom)
        self.assertEqual(st['fehler'], 1)
        self.assertEqual((d / 'S01' / 'a.nfo').read_text(), before)


if __name__ == '__main__':
    unittest.main()
