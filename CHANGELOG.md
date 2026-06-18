# Changelog

## [Unreleased]

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
