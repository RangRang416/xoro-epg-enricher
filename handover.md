# Handover — xoro-epg-enricher (2026-08-29)

**Scan-Verifikation abgeschlossen:** Task `7738148ffcd07979c7ceb148e06b3aed` lief 28.08. 14:06–18:41 UTC, `State: Idle`, `Status: Completed`. Die 5 seit 22.08. hängenden `windows-e`-Ordner sind jetzt erfasst: 277 Movie-Items (vorher 1-2), 181 erkannt (65%), 96 nicht erkannt (35%) — passt zu #32, kein neuer Befund. Nebenbei bestätigt: alle Jellyfin-Libraries haben `EnableInternetProviders: false` (by design, `enricher.py` ist einzige Metadatenquelle).

**Unverändert offen:** #29 (hängt an WI-1→WI-2, blockiert seit Juni bei `POST /Library/Refresh`), #32 (Metadaten-Lücke + Linkstation-Duplikat-Beobachtung aus #38), #37 (Backlog, F:-Laufwerk), Sehzeit-Restart-Nebenfund aus #36 (noch kein Issue, Entscheidung mit Ruben ausstehend: eigenes Issue vs. Backlog). #40/JDownloader läuft separat im Hetzner-Server-Repo.

**Sehzeit-Nebenfund behoben (29.08.):** `mount-cifs.sh` verschiebt den `docker restart jellyfin` jetzt per Jellyfin-Sessions-API-Check, wenn gerade eine Wiedergabe läuft (Details: Issue-#36-Kommentar). Getestet + deployed, kein eigenes Issue nötig.

**#32 Schicht-1-Blocker aufgelöst (29.08., FREIGABE Ruben):** <20%-Ziel bleibt verbindlich, Branch B (Jellyfin-API) reicht ohne Schreibzugriff auf buffalo-archiv. Planner-Start freigegeben (siehe Issue-#32-Kommentar).

**Nächster Schritt:** WI-2-Inventur-Spike (Opus-Subagent) läuft im Hintergrund — Ergebnis kommt als Kommentar auf #32. Bei Session-Ende vor Abschluss: nächste Session zuerst Spike-Ergebnis prüfen, dann WI-3-Zuschnitt entscheiden.
