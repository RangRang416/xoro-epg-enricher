# Changelog

## [Unreleased]

## [2026-07-01] — Wake-on-LAN für PC + Linkstation vor Abendnutzung

### Added
- `/volume1/dvb-library/wol-wake.sh` (NAS-only, nicht im Repo): Sendet WOL-Magic-Packets an Windows-PC (`2c:f0:5d:a2:c7:c0`) und Linkstation/TeraStation TS-XL/R5 (`4c:e6:76:92:53:4b`) per Python3-UDP-Broadcast (kein root nötig).
- DSM-Task 7 "WOL Wake PC+Linkstation": täglich 19:50 Uhr, einmalig (kein Repeat). 10 Min. Puffer vor typischer Sehzeit ab 20:00 Uhr.
- Bestehender Mount-Task (Task 6, alle 5 Min.) mountet danach automatisch, sobald die Geräte hochgefahren sind — keine Änderung an `mount-cifs.sh` nötig.

### Bekannte Voraussetzungen (noch zu prüfen von Ruben)
- Windows-PC: WOL muss in BIOS/UEFI + Gerätemanager-Netzwerkadapter aktiviert sein, Schnellstart deaktiviert.
- Linkstation/TeraStation: unklar ob altes Firmware (2015) im ausgeschalteten Zustand noch Standby-Strom für WOL hat — kein Admin-Zugriff zum Verifizieren.
- Kein echtes On-Demand-Wecken bei Jellyfin-Play-Klick (siehe Diskussion) — nur planmäßig um 19:50 Uhr.

## [2026-06-26] — Issue #34 + #29: Ordnernamen-Fix + leere NFO-Plots befüllen

### Fixed
- `_clean_show_name()`: Neue Funktion bereinigt Ordnernamen vor TVDb-Suche.
  Entfernt Unterstriche, Punkte-als-Trennzeichen (wenn kein Leerzeichen im Namen),
  Staffelangaben (`S04`, `Season N`, `Staffel N`) und Jahreszahlen am Ende.
  Vorher: `Goliath S04`, `Kir_Royale`, `Der.Milliardaersbunker` → 0 TVDb-Treffer.
  Nachher: `Goliath`, `Kir Royale`, `Der Milliardaersbunker` → Treffer gefunden.
- `_nfo_plot()`: Liest `<plot>` aus NFO, ignoriert führenden Release-Notes-Text.
- `scan_existing_series`: Überspringt NFO jetzt nur noch wenn `<plot>` vorhanden.
  NFOs aus Fremdquellen (vorhanden aber ohne Beschreibung) werden neu befüllt.
  Betrifft `tvshow.nfo` und Episoden-NFOs gleichermaßen.

## [2026-06-25] — Issue #32 WI-3: Metadaten für bestehende Filme (scan-existing-movies)

### Added
- `enricher.py --scan-existing-movies <dirs>`: Neuer Modus für Film-Ordner ohne RECInfo.txt (Scene-Releases, Downloads). Parst Ordnernamen, sucht per TMDb, schreibt `movie.nfo`.
- `parse_folder_title()`: Extrahiert Titel + Jahr aus Release-Style-Namen (`Title.Year.DL.1080p.x264-GROUP`) und Jellyfin-Format (`Title (Year)`). Filtert filecrypt.cc-Seiten.
- `TMDb.best_match_movie()`: TMDb-Suche mit optionalem Jahres-Filter (`primary_release_year`), automatischer Fallback ohne Jahr.
- Sammlungsordner (Harry Potter, Star.Wars, etc.) werden automatisch rekursiv aufgelöst (eine Ebene).

### Changed
- `TMDb.search_movie()` akzeptiert optionalen `year`-Parameter.

### Fixed
- 52 Filme in `/volume1/1/Filme` (bestehende-filme) mit TMDb-Metadaten versorgt; 8 Fallback-NFOs wo TMDb kein Ergebnis lieferte.
- Korrekte Behandlung von gemischten Sammlungsordnern (Sub-Folder-Filme + direktes Video).
- `_SKIP_DIRS` (`Sample`, `Subs`, `@eaDir`) werden übersprungen.

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
