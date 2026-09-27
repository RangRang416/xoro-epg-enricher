# Handover — xoro-epg-enricher (2026-09-27, Session-Ende)

**#32/WI-3.2 Vollrollout ausgeführt:** `scripts/uriinfo_hide.py` neu (Rename + Rollback, Details CHANGELOG). 168/168 Dateien umbenannt, 0 Fehler, Ruben-Freigabe im Chat. Jellyfin-DB zieht das erst beim nächtlichen 01:00-Scan nach — **noch nicht nachgemessen**.

**#52-Nebenbefund behoben + Bug selbst gefunden/korrigiert:** `scripts/touch_new_movie_folders.py` neu — deckt manuell hinzugefügte Filme ab (fehlten in "Kürzlich hinzugefügt"). Erste Fassung hatte Erstlauf-Bug (196 Filme kurzzeitig falsches Datum), sofort per Jellyfin-DateCreated zurückgesetzt + Fix committed. **Automatisierung als täglicher DSM-Task noch nicht eingerichtet** (aktuell nur manuell aufrufbar) — nächster Schritt, falls gewünscht.

**Nächste Prioritäten (meine Einschätzung, Stand 2026-09-27):**
1. Nach dem nächsten Scan `provider_coverage.py` + Stichprobe für WI-3.2, dann Issue #32 WI-3.2 abschließen, danach **WI-3.3 (Branch-B-Write-Pfad)** — größter verbleibender Hebel für die Metadaten-Lücke (Plan in `wi3-plan-metadaten-luecke.md`).
2. **#52 strukturell lösen** (Buffalo-Pfade in eigene Jellyfin-Library auslagern) — bisher nur Workaround, Fehler wiederkehrend.
3. `projekt.md` ist seit 2026-06-17 nicht mehr gepflegt (Phase VI/Serien-WI-Stand), obwohl seitdem #32/#41/#43-#52 passiert sind — widerspricht CLAUDE.md §5 ("wird ersetzt statt ergänzt", <10KB). Sollte aufgeräumt werden, bevor der nächste Planner-Spawn darauf aufbaut.

**Weiterhin offen, unverändert seit 2026-09-23:** Nachtruhe-Wunsch (nächtliche NAS-Tasks), Portfolio-Konflikt #37 ("F: einbinden") vs. #45 ("Desktop raus") — Ruben-Entscheidung ausstehend.
