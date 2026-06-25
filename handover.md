# Handover — xoro-epg-enricher (2026-06-25)

## Repo
https://github.com/RangRang416/xoro-epg-enricher

## Abgeschlossen diese Session
- **#32 WI-2**: Inventur-Spike — Root-Cause = Scene-Releases ohne RECInfo.txt
- **#32 WI-3**: `--scan-existing-movies` implementiert + deployed (commit `42e29fa`)
  - bestehende-filme: 52 erkannt, 8 Fallback
  - windows-e/Archiv/Filme_I: 30 erkannt, 4 Fallback → Jellyfin-Refresh ausgelöst
  - Jellyfin-Scan lief (heute ~19:10 gestartet)

## Noch offen #32
- **buffalo-archiv (Linkstation 192.168.2.124)**: War offline → Scan steht aus
  - Scan-Befehl wenn online:
    ```
    python3 /volume1/dvb-library/enricher.py --scan-existing-movies \
      --tmdb-key 944022b3c0d95c1d57601c7a32bc9e7f \
      --jellyfin-url http://192.168.2.9:8096 \
      --jellyfin-key 0fa51eb22d174aca876c01c8621dd1dc \
      /volume1/dvb-library/mounts/buffalo-archiv
    ```
- **Nicht verarbeitbar** in bestehende-filme: Star.Wars Ep. I/IV/VII/VIII/IX (2 Videos), Schwarzenegger/Total.Recall (direktes MKV in Collection), Terminator (6 direkte MKV)
- **Weitere windows-e Pfade prüfen**: `/windows-e/Downloads` (Jellyfin watched it)

## Absturz-Bericht 2026-06-24 22:09
- Android TV App 0.19.9: `NullPointerException` in `FullDetailsFragment.java:246`
- `getType()` auf null-BaseItemDto nach fehlgeschlagenem Playback (S01E01, 0ms)
- App-Bug, nicht server-seitig behebbar

## Nächste Session
1. **buffalo-archiv** scannen wenn Linkstation an
2. **Metadaten-Quote prüfen** nach Jellyfin-Scan (war 56% Filme / 88% Episoden)
3. **Issue #29**: Serien ohne Deutsche Beschreibung

## DSM / Docker / NAS
- docker-compose.yml: `/volume1/dvb-library/docker-compose.yml`
- CIFS Mounts: `/volume1/dvb-library/mounts/{buffalo-archiv,windows-e}`
- mount-cifs.sh: als root via DSM Task Scheduler "mount-cifs-shares"

## Jellyfin
- URL: http://192.168.2.9:8096, Key: 0fa51eb22d174aca876c01c8621dd1dc
- Library-Scan Task-ID: 7738148ffcd07979c7ceb148e06b3aed
- Serien-Library ID: 43cfe12fe7d9d8d21251e0964e0232e2
