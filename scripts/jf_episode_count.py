#!/usr/bin/env python3
"""Gibt aus, wie viele Folgen Jellyfin für die Serie unter /bestehende-serien/<Name> kennt (0, wenn unbekannt).
Verwendung: JELLYFIN_KEY=... python3 scripts/jf_episode_count.py "Fargo" """
import os, sys, urllib.parse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import inbox

url, key, name = 'http://192.168.2.9:8096', os.environ['JELLYFIN_KEY'], sys.argv[1]
try:
    res = inbox._jf(url, key, '/Items?Recursive=true&IncludeItemTypes=Series&Fields=Path&SearchTerm=' +
                    urllib.parse.quote(name), timeout=60) or {}
    sid = next((i['Id'] for i in res.get('Items', []) if (i.get('Path') or '').startswith('/bestehende-serien/')), None)
    eps = inbox._jf(url, key, f'/Shows/{sid}/Episodes?Limit=3000', timeout=90) if sid else {}
    print(len((eps or {}).get('Items', [])))
except Exception as e:
    print(f"Jellyfin-Abfrage fehlgeschlagen: {e}", file=sys.stderr)
    print(0)
