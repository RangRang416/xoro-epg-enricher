# Handover — xoro-epg-enricher (2026-09-21, Session-Ende)

**#44 (NAS-Speicherlast/"Jellyfin nicht erreichbar") erledigt.** Root Cause: `EnableRealtimeMonitor` auf Filme+Serien erzeugte 6.568/8.192 Inotify-Watches über mehrere CIFS-Mounts. Fix: Realtime-Monitor aus, Container-Neustart (Rubens Freigabe) → Watches auf 2, Jellyfin-RSS -79 MB, MemAvailable +63 MB. Zusätzlich: automatischer 12h-Scan blockierte 2 Std. in der Prime-Time (Drift-Bug) — auf festen `DailyTrigger` 01:00 umgestellt. Festplatten-Ruhezustand bestätigt aktiv (10 Min). Details/Zahlen: Issue #44.

**#45 (Desktop-PC aus Jellyfin/WOL-Kette entfernen) neu, zurückgestellt.** Ziel: Synology + Buffalo Linkstation bleiben, Desktop (~1,7 TB, nicht 7 TB wie zunächst angenommen) raus. Synology hat 7,9 TB frei, passt komfortabel. **Blockiert auf:** Hat die Linkstation (192.168.2.124) einen echten HDD-Ruhezustand? Ruben prüft selbst.

**#46/#47/#48 neu, alle zurückgestellt:**
- #46: Serien mit generischen Scene-Release-Dateinamen nicht auffindbar (Testfall: Inspector Barnaby/Midsomer Murders — auch doppelter Serien-Eintrag + unentpackte .rar-Reste gefunden).
- #47: TMDb-Jahr-Fallback bei Filmen — Scoring ohne Jahr-Berücksichtigung im Fallback, Hypothese unbestätigt (kein konkretes Beispiel).
- #48: Jellyfin-Plugins (SmartLists/Auto Collections/HoverTrailer) — Recherche fertig (Versionen/Repo-URLs dokumentiert), Installationsentscheidung offen.

**Nicht behandelt in dieser Session:** #29/#32(WI-3.3)/#37/#39/#40/#41/#42.

**Nächster Schritt:** Warten auf Rubens Linkstation-Check (#45), dann ggf. Migration planen. Sonst: nächstes Issue nach Rubens Priorität.
