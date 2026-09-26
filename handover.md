# Handover — xoro-epg-enricher (2026-09-26, Session-Ende)

**#52 (neu) — Root Cause gefunden, einmalig behoben:** Bibliotheks-Scan bricht komplett ab, sobald Buffalo-Linkstation kurz "Host is down" wirft — egal ob per API oder Jellyfin-UI ausgelöst (im Log verifiziert). Deshalb wurden "Leon, der Profi" + "Das fünfte Element" nicht erkannt, obwohl vollständig unter `/volume1/1/Filme` vorhanden. Manueller Scan bei erreichbarer Buffalo-Mount heute 19:17 Uhr erfolgreich abgeschlossen, beide Filme jetzt in Jellyfin. Strukturelles Problem bleibt offen (Issue #52, keine Lösung umgesetzt).

**Weiterhin offen, unverändert seit 2026-09-23:** Nachtruhe-Wunsch (nächtliche NAS-Tasks) — erst nachfragen was genau stören soll, bevor etwas geändert wird. Portfolio-Konflikt #37 ("F: einbinden") vs. #45 ("Desktop raus") weiterhin ungeklärt.

**Empfehlung nächste Session:** Nachtruhe-Thema zuerst, dann Lösungsrichtung für #52 (z.B. Buffalo-Pfade in eigene Bibliothek auslagern) oder #46.
