# Changelog

## [Unreleased]

## [2026-06-24] — Issue #31: CIFS-Mounts aus Docker → Bind-Mounts (nofail)

### Fixed
- Jellyfin startet jetzt auch wenn PC (192.168.2.2) und/oder Linkstation (192.168.2.124) abgeschaltet sind.
  Vorher: Docker-managed CIFS-Volumes blockierten den Container-Start bei nicht erreichbaren Hosts.
  Jetzt: Bind-Mounts auf `/volume1/dvb-library/mounts/{buffalo-archiv,windows-e}` (immer vorhanden, leer wenn CIFS nicht gemountet).

### Added
- `/volume1/dvb-library/mount-cifs.sh`: Montiert CIFS-Shares mit nofail-Logik (ping-Prüfung, graceful fallback). Startet Jellyfin nach erfolgreichem Mount neu. Log: `/volume1/dvb-library/mount-cifs.log`.
- `/volume1/dvb-library/.cifs-windows-creds` (chmod 600): Credentials-Datei für Windows-PC-Share.
- Mount-Verzeichnisse: `/volume1/dvb-library/mounts/{buffalo-archiv,windows-e}`.

### Changed
- `docker-compose.yml` (beide Pfade: `/volume1/dvb-library/` und Container Manager): CIFS-Volume-Section entfernt, zwei neue Bind-Mounts hinzugefügt.
- Alte Docker-Volumes `dvb-library_buffalo-archiv`, `dvb-library_windows-e` gelöscht.

### Pending (manueller Schritt)
- **Ruben**: DSM Task Scheduler → Ausgelöste Aufgabe bei Boot anlegen (User: root, Befehl: `/volume1/dvb-library/mount-cifs.sh`)

## [2026-06-20] — Metadaten-Bereinigung + normalize-episodes

### Added
- `enricher.py --normalize-episodes`: Erstellt Episode-NFOs für Serien mit kryptischen Dateinamen (kein S01E01-Muster). Liest TVDb-ID aus tvshow.nfo, mappt sortierte Videos sequenziell auf TVDb-Episodenliste.

### Changed
- 38 `tvshow.nfo`-Dateien: `<lockdata>true</lockdata>` entfernt (englische/spanische Beschreibungen) → TheTVDB kann beim nächsten Jellyfin-Scan deutsche Metadaten holen
- 6 `tvshow.nfo`-Dateien mit deutschen/franz. Beschreibungen bleiben unverändert (Breaking Bad, Dalgliesh 2021, Geheimnisse des Kaiserreichs, Goulag, Down Cemetery Road, Jim Bergerac)

## [2026-06-18] — WI-1/WI-3/WI-4/WI-5: Serien-Vollständig-Fix + Hardening

### Added (WI-3)
- `migrate_series.py`: einmalige Migration Flat-Folder → `Show/Season NN/` (11 Folder migriert)

### Changed (WI-5)
- Serien-Library: `EnableRealtimeMonitor=false` — enricher-seitiger `/Library/Refresh` ist einzige Refresh-Quelle; löst inotify-Limit-Erschöpfung (8192 watches)
- Jellyfin Library-Scan nach Migration getriggert

### Fixed (WI-4)
- #22: HTTP-500-Absturz war Client-seitiger NPE (stale Item-IDs nach Migration) — kein Server-Fix nötig, löst sich nach Lib-Scan + App-Neustart

---

## [2026-06-18] — WI-1: Episoden-Overview + Jellyfin-Serien-Struktur

### Added
- `TVDb.episode_overview()`: holt deutsche Episode-Overview via TVDb v4, Fallback auf EN
- `build_episode_nfo`: Fallback-Kette `episode_overview → epg_title → series.overview`

### Changed
- `move_recording` Serien-Branch: neue Zielstruktur `Show/Season NN/{basename}.*`
- NFO-Dateiname im Ziel: `{basename}.nfo` statt `movie.nfo` (Jellyfin-Sidecar-Konvention)

### Fixed
- #21: Jellyfin liest Episode-NFOs jetzt korrekt (falscher Dateiname war Ursache)

---

### Geplant
- Phase I: PoC — RECInfo.txt parsen + TMDb-Lookup + Jellyfin-Integration
- Phase II: Vollständige Python-Pipeline (RECInfo-Parser, TMDb-Client, NFO-Generator)
- Phase III: Automatisierung via Windows Task Scheduler
- Phase IV (optional): Serien-Support, Web-Dashboard
