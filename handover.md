# Handover — xoro-epg-enricher (2026-09-23, Session-Ende)

**#49 (Immich) — fertig, Ruben hat Admin-Account+Library+Scan erledigt.** Speicherlimits nachträglich gesetzt (`mem_limit` 5g/4g für Server/ML, war unbegrenzt auf 9GB gewachsen). `wsl --shutdown` für Mirrored-Netzwerkmodus (Handy-Backup) noch nicht bestätigt durchgeführt.

**#50 (neu, Immich→Jellyfin-Brücke) — Pilot erfolgreich, alle Akzeptanzkriterien erfüllt.** `scripts/immich_jellyfin_bridge.py` spiegelt ein Immich-Album als Jellyfin-Collection (read-only, kein Cron). Live verifiziert. Nächster Schritt (falls gewünscht, neues Issue): Sync-Rhythmus/Rollout auf mehr Alben — explizit nicht nachts (Rubens Nachtruhe-Vorgabe).

**Kein Code-Change an enricher.py/Jellyfin in dieser Session.**

**Bestehender Portfolio-Konflikt weiterhin offen:** #37 ("F: einbinden") widerspricht #45 ("Desktop raus") — Rubens Entscheidung steht noch aus.

**Neuer Backlog-Punkt (unkonkretisiert):** Ruben möchte bestehende nächtliche NAS-Automatiken (WOL 19:50, Bibliotheks-Scan 01:00, Kapitelbilder 02:00, Trickplay 03:00, HDD-Ruhezustand-Zyklen) überdenken ("will nachts Ruhe") — noch kein Issue, erst nachfragen was genau stört, bevor etwas geändert wird.

**Empfehlung nächste Session:** #49-Restschritte mit Ruben verifizieren (Mirrored-Modus aktiv? Immich-Backup vom Handy erreichbar?), danach #46 (kein Blocker, bereit).
