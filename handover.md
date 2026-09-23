# Handover — xoro-epg-enricher (2026-09-23, Session-Ende)

**#49 (Immich) — fertig, Ruben hat Admin-Account+Library+Scan erledigt.** Speicherlimits nachträglich gesetzt (`mem_limit` 5g/4g für Server/ML, war unbegrenzt auf 9GB gewachsen). `wsl --shutdown` für Mirrored-Netzwerkmodus (Handy-Backup) noch nicht bestätigt durchgeführt.

**#50/#51 (Immich→Jellyfin-Brücke) — voll ausgerollt + automatisiert.** `scripts/immich_jellyfin_bridge.py --all` synct alle 7 Immich-Alben zu Jellyfin-Collections (Chunking-Fix für große Alben). Windows Task Scheduler "ImmichJellyfinSync" täglich 18:00 mit Nachhol-Funktion (`StartWhenAvailable`) eingerichtet. Nebenbei Sicherheitsfund behoben: Komo-Nutzer war fälschlich Admin, jetzt korrekt `IsAdministrator: false` + granulare `EnableCollectionManagement`. Details: `[[project_immich_setup_2026-09-23]]`.

**Noch offen:** 2 Assets (Thumbnail-Dateien) konnten nicht auf Jellyfin-Items gematcht werden — unkritisch, nur Warnung im Log (`/root/immich/sync.log`).

**Kein Code-Change an enricher.py/Jellyfin in dieser Session.**

**Bestehender Portfolio-Konflikt weiterhin offen:** #37 ("F: einbinden") widerspricht #45 ("Desktop raus") — Rubens Entscheidung steht noch aus.

**Neuer Backlog-Punkt (unkonkretisiert):** Ruben möchte bestehende nächtliche NAS-Automatiken (WOL 19:50, Bibliotheks-Scan 01:00, Kapitelbilder 02:00, Trickplay 03:00, HDD-Ruhezustand-Zyklen) überdenken ("will nachts Ruhe") — noch kein Issue, erst nachfragen was genau stört, bevor etwas geändert wird.

**Empfehlung nächste Session:** #49-Restschritte mit Ruben verifizieren (Mirrored-Modus aktiv? Immich-Backup vom Handy erreichbar?), danach #46 (kein Blocker, bereit).
