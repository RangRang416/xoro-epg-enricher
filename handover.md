# Handover — xoro-epg-enricher (2026-08-26)

**#36 geschlossen** (FREIGABE Ruben 26.08.). Verifiziert: 4 saubere Trigger (23.-26.08.), Live-Inode-Vergleich Host=Container bestanden, kein Fehler im Jellyfin-Log um die Restart-Zeitpunkte.

**Neuer Fund (kein Issue, noch offen zu entscheiden):** Mounts während Rubens Sehzeit (historisch z.B. 19:25/22:58 Uhr) lösen jetzt einen `docker restart jellyfin` mitten in möglicher Wiedergabe aus — Nebenwirkung des #36-Fixes. Frage an Ruben: eigenes Issue anlegen?

**Scan-Status (Root Cause zur Handover-22.08-Frage):** Voller Scan vom 22.08. nie fertig geworden — letzter *abgeschlossener* Scan war 19.08., also VOR den 5 neuen E:-Ordnern. Die 5 Ordner haben daher nur 1-2 erfasste Items statt der erwarteten Masse. Zusätzlich 131 ffprobe-Fehler am 24.08. bei den rohen DVB-Dateien (kryptische Doppelendungen wie `.mp4.flv`) — passt zu #32. Ruben hat neuen vollen Scan auf "später" verschoben (ungünstige Uhrzeit, blockiert NAS ~1h).

**Unverändert offen:** #22 (Upstream-Jellyfin-Bug), #29 (hängt an WI-1→WI-2, seit Juni bei `POST /Library/Refresh` blockiert, `projekt.md` seit 17.06. nicht mehr gepflegt), #32 (Metadaten-Lücke), #37 (Backlog, F:-Laufwerk).

Nächster Schritt: Sehzeit-Neustart-Fund mit Ruben klären; Scan-Zeitpunkt abstimmen; danach #32 oder WI-2-Fortsetzung.
