# Handover — xoro-epg-enricher (2026-06-20 S3)

## Repo
https://github.com/RangRang416/xoro-epg-enricher

## Diese Session — Abgeschlossen

### lockdata-Bereinigung (#26)
- 38 tvshow.nfo entsperrt (englische/spanische Plots)
- 6 tvshow.nfo bleiben gesperrt (Breaking Bad, Dalgliesh 2021, Geheimnisse des Kaiserreichs, Goulag, Down Cemetery Road, Jim Bergerac)

### --normalize-episodes (#27, Commit e32759f)
- 54 Episode-NFOs für Midsomer Murders (Staffeln 1-11) erstellt
- DSM-Task täglich 09:00 läuft normalize-episodes automatisch nach
- Task-Datei: `/usr/syno/etc/synoschedule.d/root/3.task`

### Fargo S05 Struktur gefixt
- Pack-Verzeichnis (`Fargo.S05.Complete.German.DL.1080p.WEB.x264-WvF - filecrypt.cc/`) aufgelöst
- 10 Episoden + NFOs nach `/Fargo/Season 05/` flach verschoben
- Samples entfernt

### Jellyfin Library-Scan
- Gestartet (~18:34 Uhr), Jellyfin hat sich dabei intern neu gestartet
- Scan läuft noch / läuft nach Restart weiter

## Offene Issues
- #26: OFFEN — Scan-Verifikation ausstehend (Stichproben Fargo, Midsomer, Game of Thrones)

## Nächste Session — Verschachtelte Serien-Struktur (#28 erstellen)
Gleiches Problem wie Fargo bei weiteren Serien:
- **Wednesday**: `S01/EpisodeFolder/file.mkv` (2 Ebenen tief)
- **Vikings**: `Vikings 3/rsg-vikings.../Vikings.S03E10.../file.mkv` (4 Ebenen tief!)
- Lösung: generelles Flatten-Script oder neues Enricher-Feature `--flatten-downloads`

## Offene Kleinigkeiten
- `7p-809.mkv` (S08E09 Midsomer) bleibt ohne NFO (existiert nicht in TVDb)
- Down Cemetery Road + Jim Bergerac: englische Beschreibungen, lockdata behalten
- Scan-Ergebnis noch nicht verifiziert (Bernd schaut nach)
