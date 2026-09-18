#!/usr/bin/env python3
"""
provider_coverage.py — Messskript fuer Issue #32 / WI-3.

Zaehlt Movie-Items ohne ProviderId in Jellyfin, aufgeschluesselt nach Quelle
(Path-Prefix). Rein lesend: nur GET /Items, kein Write, kein Refresh, kein Scan.

Gemeinsame Kennzahl fuer WI-3.2 / WI-3.3 / WI-3.4 (Vorher-/Nachher-Vergleich).
Referenz-Baseline (2026-09-18, WI-3.1-Neuverankerung): 401 / 1310 = 30,6 %
  /bestehende-filme 179/449 · /windows-e 80/259 · /buffalo-archiv 142/602
Alte WI-2-Baseline (2026-08-29): 399/1298 (30,7%) — /bestehende-filme 169/428,
  /windows-e 88/268 (Delta -9, Ursache ungeklaert, siehe Issue-#32-Kommentar),
  /buffalo-archiv 142/602 (byte-identisch, bestaetigt Methodik).

Nur Python-3-stdlib (laeuft auf der Synology-NAS wie enricher.py).

Beispiel:
    JELLYFIN_KEY=... ./provider_coverage.py --jellyfin-url http://127.0.0.1:8096
    ./provider_coverage.py --jellyfin-key ... --json-out lauf-vorher.json
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# Library "Filme" auf der Synology. Der WI-2-Spike hat genau diese Library
# gemessen ("Movie-Items ohne ProviderId in der Library Filme"), deshalb ist sie
# die Vorgabe — sonst laufen die 9 Movie-Items der Library "Dokumentationen"
# (liegen ebenfalls unter /windows-e/) in den /windows-e-Eimer und die Zahl
# ist nicht mehr mit der Baseline vergleichbar.
DEFAULT_PARENT_ID = '7a2175bccb1f1a94152cbd2b2bae8f6d'

# Reihenfolge = Prueffolge. Laengster Prefix zuerst waere hier egal (disjunkt),
# aber die Reihenfolge ist die des WI-2-Kommentars.
DEFAULT_PREFIXES = ['/bestehende-filme', '/windows-e', '/buffalo-archiv']

BASELINE = {
    '/bestehende-filme': (179, 449),
    '/windows-e': (80, 259),
    '/buffalo-archiv': (142, 602),
    '_total': (401, 1310),
}


def http_get_json(url, params=None, timeout=900):
    if params:
        url = url + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, method='GET')
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def fetch_items(base_url, api_key, parent_id, page_size, timeout, verbose=False):
    """Holt alle Movie-Items. Paginiert, wenn --page-size gesetzt ist.

    Gibt (items, total_record_count) zurueck. Die NAS ist langsam (1 GB RAM);
    ein einzelner Request ueber ~1300 Items dauert dort 1-3 Minuten, deshalb
    der grosszuegige Default-Timeout.
    """
    base = base_url.rstrip('/') + '/Items'
    params = {
        'Recursive': 'true',
        'IncludeItemTypes': 'Movie',
        'Fields': 'ProviderIds,Path',
        'EnableTotalRecordCount': 'true',
        'api_key': api_key,
    }
    if parent_id:
        params['ParentId'] = parent_id

    if not page_size:
        data = http_get_json(base, params, timeout)
        return data.get('Items', []), data.get('TotalRecordCount')

    items, total, start = [], None, 0
    while True:
        p = dict(params, Limit=page_size, StartIndex=start)
        data = http_get_json(base, p, timeout)
        batch = data.get('Items', [])
        if total is None:
            total = data.get('TotalRecordCount')
        items.extend(batch)
        if verbose:
            print('  ... %d / %s' % (len(items), total), file=sys.stderr)
        if not batch or (total is not None and len(items) >= total):
            break
        start += page_size
    return items, total


def bucket_of(path, prefixes):
    for pre in prefixes:
        if path == pre or path.startswith(pre.rstrip('/') + '/'):
            return pre
    return 'OTHER'


def analyse(items, prefixes):
    stats = {p: {'total': 0, 'missing': 0} for p in prefixes}
    stats['OTHER'] = {'total': 0, 'missing': 0}
    other_paths = []
    provider_hist = {}
    no_path = 0

    for it in items:
        path = it.get('Path') or ''
        if not path:
            no_path += 1
        b = bucket_of(path, prefixes)
        if b == 'OTHER' and len(other_paths) < 25:
            other_paths.append(path)
        stats[b]['total'] += 1

        # "ohne ProviderId" = Feld fehlt, ist None, oder ist ein leeres Dict.
        # Jellyfin liefert bei Items ohne Provider ein {} statt das Feld
        # wegzulassen — beides zaehlt.
        pids = it.get('ProviderIds') or {}
        pids = {k: v for k, v in pids.items() if v}
        if not pids:
            stats[b]['missing'] += 1
        key = ','.join(sorted(pids)) or '(keine)'
        provider_hist[key] = provider_hist.get(key, 0) + 1

    return stats, other_paths, provider_hist, no_path


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--jellyfin-url', default=os.environ.get('JELLYFIN_URL', 'http://127.0.0.1:8096'))
    ap.add_argument('--jellyfin-key', default=os.environ.get('JELLYFIN_KEY'),
                    help='API-Key; besser per Env JELLYFIN_KEY (steht sonst in der Shell-History)')
    ap.add_argument('--parent-id', default=DEFAULT_PARENT_ID,
                    help='Library-Id. "" = alle Libraries (aendert die Zahl!). '
                         'Default: Library "Filme" (= WI-2-Baseline)')
    ap.add_argument('--prefix', action='append', dest='prefixes', default=None,
                    help='Quell-Prefix, mehrfach angebbar. Default: %s' % ' '.join(DEFAULT_PREFIXES))
    ap.add_argument('--page-size', type=int, default=0,
                    help='Paginieren mit dieser Seitengroesse (0 = ein Request)')
    ap.add_argument('--timeout', type=int, default=900)
    ap.add_argument('--items-file',
                    help='Statt API: bereits gespeicherte /Items-JSON-Antwort auswerten')
    ap.add_argument('--json-out', help='Ergebnis zusaetzlich als JSON hierhin schreiben')
    ap.add_argument('--no-baseline', action='store_true',
                    help='Vergleich gegen die WI-2-Baseline unterdruecken')
    ap.add_argument('-v', '--verbose', action='store_true')
    args = ap.parse_args()

    prefixes = args.prefixes or DEFAULT_PREFIXES

    if args.items_file:
        with open(args.items_file, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
        items = data.get('Items', data if isinstance(data, list) else [])
        total_rc = data.get('TotalRecordCount') if isinstance(data, dict) else len(items)
        source = args.items_file
    else:
        if not args.jellyfin_key:
            ap.error('Kein API-Key: --jellyfin-key oder Env JELLYFIN_KEY setzen.')
        try:
            items, total_rc = fetch_items(args.jellyfin_url, args.jellyfin_key,
                                          args.parent_id, args.page_size,
                                          args.timeout, args.verbose)
        except urllib.error.HTTPError as e:
            print('HTTP %s von Jellyfin: %s' % (e.code, e.reason), file=sys.stderr)
            return 2
        except Exception as e:                                    # noqa: BLE001
            print('Abruf fehlgeschlagen: %r' % (e,), file=sys.stderr)
            return 2
        source = args.jellyfin_url + ' ParentId=' + (args.parent_id or '(alle)')

    stats, other_paths, provider_hist, no_path = analyse(items, prefixes)

    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    print('provider_coverage  %s' % ts)
    print('Quelle: %s' % source)
    print('TotalRecordCount=%s  geholt=%d%s' % (
        total_rc, len(items),
        '' if total_rc in (None, len(items)) else '   *** ABWEICHUNG: Ergebnis unvollstaendig ***'))
    if no_path:
        print('Items ohne Path: %d (landen im Eimer OTHER)' % no_path)
    print('')

    hdr = '%-22s %8s %9s %8s' % ('Quelle', 'Items', 'ohne PID', 'Quote')
    print(hdr)
    print('-' * len(hdr))
    t_tot = t_mis = 0
    for p in prefixes + ['OTHER']:
        s = stats[p]
        if p == 'OTHER' and s['total'] == 0:
            print('%-22s %8d %9d %8s' % (p, 0, 0, '-'))
        else:
            q = (100.0 * s['missing'] / s['total']) if s['total'] else 0.0
            print('%-22s %8d %9d %7.1f%%' % (p, s['total'], s['missing'], q))
        t_tot += s['total']
        t_mis += s['missing']
    print('-' * len(hdr))
    quote = (100.0 * t_mis / t_tot) if t_tot else 0.0
    print('%-22s %8d %9d %7.1f%%' % ('SUMME', t_tot, t_mis, quote))
    print('')

    if other_paths:
        print('!! OTHER ist nicht leer — Prefix-Liste deckt nicht alles ab:')
        for p in other_paths:
            print('   %s' % p)
        print('')

    print('ProviderId-Kombinationen:')
    for k, v in sorted(provider_hist.items(), key=lambda kv: -kv[1]):
        print('   %-30s %5d' % (k, v))
    print('')

    if not args.no_baseline:
        print('Vergleich WI-2-Baseline (2026-08-29):')
        for p in prefixes:
            if p in BASELINE:
                bm, bt = BASELINE[p]
                s = stats[p]
                print('   %-22s Items %+d (%d->%d)   ohne PID %+d (%d->%d)' % (
                    p, s['total'] - bt, bt, s['total'], s['missing'] - bm, bm, s['missing']))
        bm, bt = BASELINE['_total']
        print('   %-22s Items %+d (%d->%d)   ohne PID %+d (%d->%d)' % (
            'SUMME', t_tot - bt, bt, t_tot, t_mis - bm, bm, t_mis))
        if (t_mis, t_tot) == (bm, bt):
            print('   => Baseline exakt reproduziert.')
        else:
            print('   => ABWEICHUNG zur Baseline. Vor Weiterarbeit klaeren (WI-3.1-Stoppkriterium).')
        print('')

    if args.json_out:
        out = {
            'timestamp': ts,
            'source': source,
            'parent_id': args.parent_id,
            'prefixes': prefixes,
            'total_record_count': total_rc,
            'fetched': len(items),
            'per_source': {p: stats[p] for p in prefixes + ['OTHER']},
            'total': {'total': t_tot, 'missing': t_mis, 'quote_pct': round(quote, 2)},
            'provider_histogram': provider_hist,
        }
        with open(args.json_out, 'w', encoding='utf-8') as fh:
            json.dump(out, fh, ensure_ascii=False, indent=2)
        print('JSON geschrieben: %s' % args.json_out)

    return 0


if __name__ == '__main__':
    sys.exit(main())
