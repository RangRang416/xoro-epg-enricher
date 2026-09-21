# Handover — xoro-epg-enricher (2026-09-21, Session-Ende)

**#44 (NAS-Speicherlast) erledigt + geschlossen.** Root Cause: Inotify-Watches (6.568/8.192) durch `EnableRealtimeMonitor` auf Filme/Serien. Fix: aus + Neustart → Watches auf 2, +79 MB Jellyfin-Puffer. Scan-Trigger von driftendem 12h-Intervall auf festen `DailyTrigger` 01:00 umgestellt (verhinderte 2h-Blockade in der Prime-Time). HDD-Ruhezustand bestätigt aktiv (10 Min) — Syn. muss ab jetzt durchgehend an bleiben (kein RTC-Wake), Platten schlafen von selbst.

**Grundprüfung Pipeline (auf Rubens Wunsch):** Bibliotheks-Aufnahme ✅, Abspielbarkeit ✅ (auch HEVC-Altfall "Glückliche Männer", weiterhin Direct Play ohne Transcoding). Erkennung neuer Aufnahmen nicht testbar ohne physisch eingesteckten Xoro-Stick.

**Neu angelegt, alle zurückgestellt:** #45 (Desktop aus Jellyfin-Kette, blockiert auf Rubens Linkstation-Ruhezustand-Check), #46 (generische Serien-Dateinamen, Testfall Barnaby + jetzt auch GoT/Euphoria belegt, fertig diagnostiziert), #47 (TMDb-Jahr-Fallback, unbestätigte Hypothese), #48 (Plugin-Entscheidung, Recherche fertig).

**Ungeklärter Portfolio-Konflikt:** #37 ("F: einbinden") widerspricht #45 ("Desktop raus") — Rubens Entscheidung aussteht, vermutlich #37 obsolet.

**Empfehlung nächste Session:** #46 zuerst (kein Blocker, bereit).
