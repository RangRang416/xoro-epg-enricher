# Projekt: Xoro-Aufnahmen mit EPG-Beschreibung anreichern

## Ziel

Aufnahmen des Xoro HRT 8772 HDD nachträglich mit den Sendungsbeschreibungen des elektronischen Programmführers (EPG) versehen, sodass die Filmsammlung auch nach Wochen oder Monaten zuverlässig zugeordnet werden kann.

## Problem

Der Xoro-Receiver speichert Aufnahmen zwar als Standard-`.ts`-Dateien, aber die EPG-Beschreibung wird nicht in die Datei eingebettet und auch nicht als Sidecar abgelegt. Im Dateinamen stehen lediglich Sender, Datum und Uhrzeit (sowie meist der Sendungstitel). Damit lässt sich später nicht mehr nachvollziehen, worum es im Film inhaltlich ging — Genre, Regie, Inhaltsangabe und Bewertung fehlen.

## Architektur

```
┌─────────────────┐
│ Xoro-Receiver   │  → .ts-Dateien auf SATA-HDD oder USB-Stick
└─────────────────┘
        │ (Datenträger an PC, Watch-Folder)
        ▼
┌─────────────────┐         ┌──────────────────┐
│ n8n-Workflow    │ ◄────── │ XMLTV-Feed       │
│ (Match-Engine)  │         │ (täglicher Pull) │
└─────────────────┘         └──────────────────┘
        │                           │
        ▼                           ▼
┌─────────────────┐         ┌──────────────────┐
│ .nfo-Sidecar    │         │ EPG-Datenbank    │
│ neben .ts-Datei │         │ (SQLite/Postgres)│
└─────────────────┘         └──────────────────┘
```

## Komponenten

### Hardware

- **Xoro HRT 8772 HDD** mit interner SATA-Festplatte (Wechselrahmen über Frontblende) oder USB-Massenspeicher als Aufnahmemedium.
- **Empfehlung:** USB-Stick statt interner Platte verwenden — entfällt das Aushängen, Stick einfach an den PC stecken.

### EPG-Quelle

Primärkandidat: **iptv-org/epg** auf GitHub — offene XMLTV-Feeds für deutsche Sender, täglich aktualisiert. Alternativen: `epg.pw`, `xmltv.se` (kostenpflichtig).

Pull-Frequenz: einmal täglich, Aufbewahrung mindestens 30 Tage (Puffer für späte Übertragungen vom Xoro).

### Datenbank

SQLite reicht für den Anwendungsfall vollständig. Schema:

```sql
CREATE TABLE epg (
  id INTEGER PRIMARY KEY,
  channel TEXT NOT NULL,        -- z.B. "ZDF", "NDR"
  start_utc DATETIME NOT NULL,
  stop_utc DATETIME NOT NULL,
  title TEXT NOT NULL,
  sub_title TEXT,
  description TEXT,
  category TEXT,
  year INTEGER,
  country TEXT,
  rating TEXT,
  raw_xml TEXT
);
CREATE INDEX idx_channel_time ON epg(channel, start_utc);
```

### n8n-Workflow

**Workflow A — EPG-Sync (täglich):**

1. Cron-Trigger 06:00 Uhr.
2. HTTP-Request: XMLTV-Feed laden.
3. Function-Node: XML parsen, Datensätze normalisieren.
4. SQLite-Insert mit `INSERT OR REPLACE`.
5. Datensätze älter als 30 Tage löschen.

**Workflow B — Aufnahme-Matching (manuell oder per Watch-Folder):**

1. Trigger: neue `.ts`-Datei in Eingangsordner.
2. Function-Node: Dateiname parsen → Sender, Startzeit extrahieren.
3. SQLite-Query: Eintrag finden mit `channel = ? AND start_utc BETWEEN start ± 5 min`.
4. Function-Node: `.nfo`-Datei (Kodi-Schema) zusammenbauen.
5. Datei neben `.ts` ablegen, Aufnahme in Zielordner verschieben.
6. Match-Log schreiben (für Fehleranalyse bei Treffern unter 100 %).

### Sidecar-Format (.nfo, Kodi-Standard)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<movie>
  <title>The Courier - Tödlicher Auftrag</title>
  <originaltitle>The Courier</originaltitle>
  <year>2019</year>
  <plot>Eine Kurierin wird in London in einen tödlichen Auftrag verwickelt …</plot>
  <genre>Actionthriller</genre>
  <country>GB</country>
  <country>USA</country>
  <studio>ZDF</studio>
  <aired>2026-04-26</aired>
</movie>
```

Plex, Kodi und Jellyfin lesen dieses Format direkt. Eine spätere Migration der Sammlung in eine richtige Mediathek bleibt offen.

## Einschränkungen

- **Verschlüsselte Aufnahmen:** Privatsender via freenet-TV (Irdeto Cloaked CA) sind gerätegebunden verschlüsselt. Diese `.ts`-Dateien lassen sich nicht extern abspielen und fallen damit aus dem Konzept. Öffentlich-rechtliche Sender (ARD, ZDF, Dritte, Arte, 3sat etc.) sind unverschlüsselt.
- **Sender-Mapping:** Der Xoro nutzt eigene Sendernamen im Dateinamen (z.B. „NDR FS NDS HD"). Diese müssen einmalig auf die XMLTV-IDs gemappt werden — Mapping-Tabelle in der DB pflegen.
- **Zeitabweichung:** Xoro-Timer haben oft Vor-/Nachlauf von 1–5 Minuten. Match-Toleranz mit ±5 Minuten beginnen, gegebenenfalls auf ±10 erhöhen.
- **Mehrere Sendungen im Aufnahmefenster:** Bei Vor-/Nachlauf, der eine Nachbarsendung anschneidet, wird die längere Sendung als Treffer gewählt (Heuristik: jene, die zeitlich am stärksten überlappt).

## Offene Fragen

1. **Dateinamen-Schema:** Vor Implementierung drei bis fünf Beispiel-Dateinamen sammeln, um das exakte Trennzeichen-Muster zu kennen. Erwartet wird etwa: `<Sender>_<YYYYMMDD>_<HHMM>_<Titel>.ts`.
2. **Sammlung schon vorhandener Aufnahmen:** Einmalige Bulk-Operation über alle Bestandsaufnahmen — funktioniert nur, solange das XMLTV-Archiv weit genug zurückreicht. Für ältere Aufnahmen Fallback auf manuelles Nachschlagen über `wunschliste.de` oder `fernsehserien.de`.
3. **n8n-Hosting:** Auf vorhandenem Hetzner-Server mitlaufen lassen oder lokal? Bei lokal entfällt der Upload großer `.ts`-Dateien.

## Nächste Schritte

- [ ] Drei bis fünf Beispiel-Dateinamen aus aktuellen Xoro-Aufnahmen extrahieren und Schema dokumentieren.
- [ ] iptv-org/epg-Feed auf Vollständigkeit der relevanten Sender prüfen (ZDF, NDR, MDR, ZDFneo, Arte, 3sat etc.).
- [ ] Sender-Mapping-Tabelle anlegen (Xoro-Name ↔ XMLTV-ID).
- [ ] n8n-Workflow A (EPG-Sync) implementieren und drei Tage laufen lassen.
- [ ] Workflow B mit fünf Testaufnahmen durchspielen, Match-Quote messen.
- [ ] Bulk-Import der Bestandsaufnahmen, sobald Match-Quote > 90 %.

## Referenzen

- Xoro HRT 8772 HDD: <https://www.xoro.de/produkte/details/xoro-hrt-8772-hdd-2/>
- iptv-org/epg: <https://github.com/iptv-org/epg>
- Kodi NFO-Schema: <https://kodi.wiki/view/NFO_files/Movies>
- DVR Studio UHD (Haenlein, kommerziell, falls Werkzeug für TS-Bearbeitung gebraucht wird): über xoro.de verlinkt.
