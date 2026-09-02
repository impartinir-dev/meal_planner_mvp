# NutriMatch DE

**Version 0.6.0** — Invite-only Wochenplaner für Deutschland. Kitchen OS matcht eigene Rezepte auf **Lidl- und Marktkauf-Preise**, skaliert den Haushalt, und zieht Vorrat vor dem Einkauf ab.

UI auf Deutsch. Rezeptküche international. Sub-10-Minuten meint aktive Zeit.

## Was es kann

- Dashboard unter `/` (heute kochen, Woche, Vorrat)
- Wochenplan Mo–So × Früh / Mittag / Abend, tauschen, fixieren, gekocht
- Profil: Familie, Mitbewohner, kcal/Protein pro Person (1–6). Der Plan nimmt die **Summe** und kocht so viele Portionen
- Küchengeräte-Filter (ohne Ofen keine Ofengerichte)
- Einkaufszettel in Packungen, Druck: zwei A5 auf einem A4 mit Schnittlinie
- Zero Waste: persistenter Vorratsschrank (Plus), Abzug nach „Gekocht“, Kassenbon-OCR (Premium)

## Märkte

Im Picker nur Stores **mit aktuellen Preisen**: **Lidl** und **Marktkauf**.  
REWE, ALDI Süd, Kaufland, EDEKA sind Roadmap, keine Fake-Optionen.

**Preise kommen nicht von einem Live-Scraper.** Kitchen OS lädt gespeicherte Prospekt-JSON-Fixtures, legt ein Review-Batch an, und `promote` schreibt aktuelle `PriceObservation` / `Offer`. Leeres Batch überschreibt den letzten guten Preis nicht. Rezeptimport legt fehlende SKUs mit Platzhalter-Discounterpreisen an (`source=import`), bis eine echte Beobachtung sie ersetzt. Die alte Admin-Seite **Angebote** (`deals.json`) gehört zum früheren JSON-Planer, nicht zum Matcher.

## Abo

| | Free | Plus 4,99 €/Monat | Premium 8,99 €/Monat |
| --- | --- | --- | --- |
| Wochenplan, Tausch, Druck | ja | ja | ja |
| Haushalt + Küche | ja | ja | ja |
| Vorratsschrank + Reste abziehen | — | ja | ja |
| Kassenbon-OCR | — | — | ja |

Checkout (Stripe) kommt später. Der Admin schaltet Konten unter **Admin** frei. `/pro` zeigt immer die Kaufmaske (auch für Admin, als Vorschau).

OCR braucht `XAI_API_KEY` (xAI, grok-4.6).

## Lokal starten

```bash
pip install -r backend/requirements.txt
python -m backend.seed
```

Terminal 1:

```bash
set PYTHONPATH=.
flask --app backend run --port 5000
```

PowerShell: `$env:PYTHONPATH = "."`

Terminal 2:

```bash
cd frontend
npm install
npm run dev
```

App: **http://127.0.0.1:5173/** (Vite hängt auf IPv4). API: http://127.0.0.1:5000

Beim Flask-Start: kleines Seed-Katalog + Import von `recipes.txt` (idempotent), damit ~90 Gerichte shoppable sind.

Standard-Admin (Env überschreibbar):

- `ADMIN_EMAIL` (default `admin@localhost`)
- `ADMIN_PASSWORD` (default `changeme-now`)

`python -m backend.seed` legt den Admin an und druckt Einladungscodes.

## Docker

```bash
docker compose up --build
```

Dann http://127.0.0.1:8000 — einloggen, unter **Einladungen** Codes erzeugen.

In Produktion: eigenes `SECRET_KEY` und Admin-Passwort.

## Tests

```bash
python -m pytest tests/ -q
```
