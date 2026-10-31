#!/usr/bin/env python3
"""Gibt aus, wie viele Folgen Jellyfin für die Serie im Ordner /bestehende-serien/<Ordnername> mit Staffel- und Folgennummer kennt
(0, wenn unbekannt). Gesucht wird über den Ordnerpfad, nicht über den Namen: Jellyfin führt Serien oft unter dem TVDB-Namen
(Ordner "Jim Bergerac ermittelt" = Serie "Bergerac"). Folgen ohne Nummer sind unbearbeitete Platzhalter und zählen nicht.
Verwendung: JELLYFIN_KEY=... python3 scripts/jf_episode_count.py "Fargo" """
import os, sys, urllib.parse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import inbox

url, key, name = 'http://192.168.2.9:8096', os.environ['JELLYFIN_KEY'], sys.argv[1]
try:
    res = inbox._jf(url, key, '/Items?Recursive=true&IncludeItemTypes=Series&Fields=Path', timeout=120) or {}
    sid = next((i['Id'] for i in res.get('Items', []) if (i.get('Path') or '') == f'/bestehende-serien/{name}'), None)
    eps = inbox._jf(url, key, f'/Shows/{sid}/Episodes?Limit=3000', timeout=90) if sid else {}
    print(sum(1 for e in (eps or {}).get('Items', []) if e.get('IndexNumber') is not None))
except Exception as e:
    print(f"Jellyfin-Abfrage fehlgeschlagen: {e}", file=sys.stderr)
    print(0)
