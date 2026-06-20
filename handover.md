# Handover — xoro-epg-enricher (2026-06-20 S2)

## Repo
https://github.com/RangRang416/xoro-epg-enricher

## Diese Session

### lockdata-Bereinigung (#26)
- 38 tvshow.nfo: `<lockdata>true</lockdata>` entfernt (englische/spanische Plots)
- 6 tvshow.nfo bleiben gesperrt (Breaking Bad, Dalgliesh 2021, Geheimnisse des Kaiserreichs, Goulag, Down Cemetery Road, Jim Bergerac)
- Ziel: Jellyfin-Scan holt deutsche Beschreibungen via TheTVDB

### normalize-episodes (#27, Commit e32759f)
- Neuer Flag `--normalize-episodes` in enricher.py implementiert und deployed
- 54 Episode-NFOs für Midsomer Murders (Staffeln 1-11) erstellt
- Logik: TVDb-ID aus tvshow.nfo → Episodennummer aus Dateiname (z.B. 7p-704 → S07E04)
- NxEN-Format (z.B. Voyager `1xE01`) wird erkannt → korrekt übersprungen
- Episode-00-Dateien (7p-100) übersprungen
- 1 Fehler: `7p-809` → S08E09 existiert nicht in TVDb (Season 8 hat 8 Folgen)

## Issues
- #25: CLOSED (Sclotland Yard, letzte Session)
- #26: OFFEN — Jellyfin-Scan ausstehend (Bernd gibt OK)
- #27: CLOSED nach Commit e32759f
- #13, #14: Optional, niedrige Prio

## DSM-Task (täglich 09:00)
- Schritt 1: normaler Enricher (neue Xoro-Aufnahmen)
- Schritt 2: `--normalize-episodes` (neue Serien mit kryptischen Dateinamen → automatisch NFOs)
- Task-Datei: `/usr/syno/etc/synoschedule.d/root/3.task`

## Nächster Schritt
**Jellyfin Library-Scan** — Bernd gibt OK (blockiert NAS ~1-2h):
- TheTVDB holt deutsche Beschreibungen für 38 Serien
- Jellyfin liest neue Episode-NFOs für Midsomer Murders

## Offene Kleinigkeiten
- `7p-809.mkv` (S08E09) bleibt ohne NFO — evtl. Sonderepisode oder falsch nummeriert
- Down Cemetery Road + Jim Bergerac: englische Beschreibungen, aber lockdata behalten (Zoë/Étrangers-Heuristik) — manuell korrigierbar bei Bedarf
