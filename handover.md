# Handover — xoro-epg-enricher (2026-08-07)

**#35 (Mount-Diagnose vom 20.07 war falsch/unvollständig, jetzt korrigiert):** Ursache des tatsächlichen Ausfalls war NICHT der Mount, sondern der Jellyfin-Docker-Container selbst — startet nach dem täglichen NAS-Boot (08:00 Uhr, Power-Schedule) mit einem Race gegen den CIFS-Remount und bleibt dann im Status `Created` hängen (Docker-Restart-Policy greift hier nicht). Manuell gefixt (`docker start jellyfin`) + präventiv: `mount-cifs.sh` (NAS-only, Cron alle 5 Min.) prüft jetzt zusätzlich den Jellyfin-Status und startet ihn bei Bedarf neu. **Noch nicht verifiziert** — abwarten, ob der morgendliche Aussetzer ausbleibt. Details: `project_xoro_issue22_35_diagnosis_2026-07-20.md` (Memory).

**#22:** unverändert seit 20.07, weiter offen, kein neuer Stand diese Session.

Offen, unverändert seit 01.07.: zweiter Serien-Scan auf `buffalo-archiv/Filme II/Serien`-Rest, #32 Metadaten-Lücke.

Beide Issues (#22/#35) bleiben offen bis Rubens Freigabe zum Schließen.
