# Handover — xoro-epg-enricher (2026-09-23, Session-Ende)

**#49/#50/#51 (Immich→Jellyfin) — komplett fertig, live im Einsatz.** Immich läuft PC-seitig (WSL2, nativer Docker, RAM-Limits gesetzt nach Anfangsspitze). `scripts/immich_jellyfin_bridge.py --all` synct alle 7 Immich-Alben zu Jellyfin-Collections, Windows Task Scheduler täglich 18:00 mit Nachhol-Funktion. Nebenbei behoben: Komo-Jellyfin-Nutzer war fälschlich Admin (jetzt korrekt eingeschränkt). Details: `[[project_immich_setup_2026-09-23]]`.

**OFFEN, noch nicht angegangen: Nachtruhe-Wunsch.** Ruben will nachts (ab ca. 22 Uhr, Router-Abschaltung) nichts Aktives am/über den PC oder im Netz haben. Betrifft potenziell die bestehenden NAS-Nacht-Tasks (WOL 19:50, Bibliotheks-Scan 01:00, Kapitelbilder 02:00, Trickplay 03:00, HDD-Ruhezustand-Zyklen). Ungeklärt: kappt die Router-Abschaltung auch die NAS-eigene Netzwerkverbindung (Heimnetz-Topologie unbekannt)? **Nächste Session: gezielt nachfragen, was genau stören soll, bevor etwas geändert wird — noch kein Issue angelegt.**

**Bestehender Portfolio-Konflikt weiterhin offen:** #37 ("F: einbinden") widerspricht #45 ("Desktop raus") — Rubens Entscheidung steht noch aus.

**Empfehlung nächste Session:** Nachtruhe-Thema zuerst (s.o.), dann #46 (kein Blocker, bereit).
