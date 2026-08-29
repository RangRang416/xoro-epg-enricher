# Handover — xoro-epg-enricher (2026-08-29, Session-Ende, 7d-Kontingent 88%)

**Scan-Verifikation abgeschlossen:** Task `7738148ffcd07979c7ceb148e06b3aed` lief 28.08. 14:06–18:41 UTC, Completed. Die 5 seit 22.08. hängenden `windows-e`-Ordner sind erfasst: 277 Movie-Items (vorher 1-2), 181 erkannt (65%). Nebenbei bestätigt: alle Jellyfin-Libraries haben `EnableInternetProviders: false` (by design, `enricher.py` ist einzige Metadatenquelle).

**Sehzeit-Nebenfund aus #36 behoben+deployed (29.08.):** `mount-cifs.sh` auf der NAS verschiebt `docker restart jellyfin` jetzt per Jellyfin-Sessions-API-Check, wenn gerade eine Wiedergabe läuft, statt sie abzubrechen (Details: Issue-#36-Kommentar). Getestet (Syntax + realer Lauf), kein eigenes Issue nötig. Backup: `mount-cifs.sh.bak-2026-08-29` auf der NAS.

**#32 komplett durchgeplant (29.08.):** Schicht-1-Blocker aufgelöst (FREIGABE Ruben: <20%-Ziel verbindlich, Branch B reicht ohne Schreibzugriff buffalo-archiv) → WI-2-Inventur-Spike (Opus, read-only) → WI-3-Plan (Opus). Volltext: `wi3-plan-metadaten-luecke.md` im Repo, Kurzfassung + WI-2-Rohdaten als Issue-#32-Kommentare.

**WI-2-Kernbefund:** Die "141 ohne Metadaten" sind zu 95% ein Phantom-Bug — `URIInfo.bin`-Dateien, die Jellyfin fälschlich als eigene Filme zählt (160 von 169), nicht der Enricher. Library-weite Lücke real 30,7% (399/1298), nach Bereinigung 21,0%. **Korrektur einer eigenen Fehlmessung von mir in dieser Session:** meine Zwischenzahl "61% parsbar" war ein falsch interpretierter Dry-Run-Zähler (real 42,7%) — durch den Spike ohnehin überholt.

**WI-3-Plan (wartet auf Freigabe zum Start, noch NICHT erteilt):** 6 Work-Items, aber nur 3 fürs Ziel nötig — WI-3.1 (Spike: Ausschlussmechanismus + Messskript, Opus/Sonnet) → WI-3.2 (URIInfo.bin-Pilot 2 Ordner, Sonnet/Opus) → WI-3.3 (Branch-B-Write mit Score-Gate+Snapshot, Sonnet/Opus) erreichen rechnerisch 16,1%, unter dem Ziel. WI-3.4 (Titel-Normalisierung), Serien-Extraktion, VIDEO_EXTS-Erweiterung sind Reserve/zurückgestellt. Wichtiges Gate: nach WI-3.1 ggf. Ruben-Entscheidung nötig, falls URIInfo.bin nur per Nenner-Bereinigung statt echtem Ausschluss lösbar ist.

**Unverändert offen:** #29 (hängt an WI-1→WI-2 des Serien-Projekts, blockiert seit Juni bei `POST /Library/Refresh`), #37 (Backlog, F:-Laufwerk), Linkstation-Duplikat-Beobachtung aus #38 (noch nicht untersucht). #40/JDownloader läuft separat im Hetzner-Server-Repo weiter.

**Nächster Schritt:** projekt.md ist erst NACH Rubens Freigabe zum WI-3-Start zu aktualisieren (Planner hat das bewusst noch nicht getan, §5). Session endete auf Rubens Wunsch wegen 7d-Kontingent (88%) — WI-3.1 noch nicht freigegeben, erst dokumentiert. Nächste Session: Freigabe einholen, dann WI-3.1 starten.
