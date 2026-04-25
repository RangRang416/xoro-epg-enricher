# xoro-epg-enricher

Xoro HRT 8772 Aufnahmen automatisch mit Metadaten aus TMDb anreichern und als Jellyfin-Mediathek auf dem Android-Handy zugänglich machen.

## Architektur

```
N:\PVR\REC\00NNN\RECInfo.txt
       ↓ (Titel + Sender)
  TMDb API Lookup
       ↓ (Plot, Genre, Jahr, Bewertung, Cover)
  record.ts.nfo + poster.jpg neben record.ts
       ↓
  Jellyfin (lokal, Windows)
       ↓
  Jellyfin Android-App
```

## Voraussetzungen

- Python 3.11+
- [TMDb API-Key](https://www.themoviedb.org/settings/api) (kostenlos)
- [Jellyfin](https://jellyfin.org/) lokal installiert
- Aufnahmen auf gemapptem Netzlaufwerk (z.B. `N:\PVR\REC\`)

## Setup

```bash
git clone https://github.com/RangRang416/xoro-epg-enricher.git
cd xoro-epg-enricher
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# TMDB_API_KEY in .env eintragen
```

## Verwendung

```bash
# Einzelnen Aufnahme-Ordner verarbeiten
python -m xoro_enricher.cli enrich --path "N:\PVR\REC\00029"

# Alle Aufnahmen verarbeiten (überspringt bereits verarbeitete)
python -m xoro_enricher.cli enrich --root "N:\PVR\REC"

# Erzwingen (auch bereits verarbeitete)
python -m xoro_enricher.cli enrich --root "N:\PVR\REC" --force
```

## Automatisierung

Windows Task Scheduler läuft alle 10 Minuten:

```powershell
.\scripts\install-task.ps1
```

## Jellyfin

Siehe `docs/jellyfin-setup.md`.
