# Handover — xoro-epg-enricher (2026-09-27, Session-Ende)

**#32/WI-3.2 Vollrollout ausgeführt:** `scripts/uriinfo_hide.py` neu (Rename + Rollback). 168/168 umbenannt, 0 Fehler. Jellyfin-DB zieht das erst beim nächtlichen 01:00-Scan nach — **noch nicht nachgemessen**.

**#52-Nebenbefund behoben:** `scripts/touch_new_movie_folders.py` neu (deckt manuell hinzugefügte Filme ab). Selbstgefundener Erstlauf-Bug sofort korrigiert (Details CHANGELOG). **Automatisierung als täglicher DSM-Task noch nicht eingerichtet.**

`projekt.md` aufgeräumt (war seit Juni veraltet) + #22/#29-Stand aus Issue-Kommentaren nachgezogen. **#22 geschlossen** (Root Cause bekannt, bewusst kein Fix, Upstream-Wartestellung).

**Nächste Prioritäten:** (1) Nachmessung WI-3.2 nach nächtlichem Scan, dann WI-3.3 (Branch-B-Write-Pfad, größter Hebel für #32). (2) #52 strukturell lösen (Buffalo-Pfade eigene Library). (3) #29 hängt an WI-2 (Episode-TypeOptions, seit Juni unverändert) — Stand vor Wiederaufnahme neu prüfen.

**Weiterhin offen:** Nachtruhe-Wunsch vs. nächtliche NAS-Tasks, Portfolio-Konflikt #37 vs. #45 — Ruben-Entscheidung ausstehend.
