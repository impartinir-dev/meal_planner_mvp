# NutriMatch DE

**Version 0.4.0** — Invite-only Wochenplaner. Nur noch Rezepte mit echten Schritten, jedes Gericht höchstens einmal pro Woche.

Invite-only Wochenplaner: Mahlzeiten nach **Ernährungsziel, Budget und kuratierten Supermarkt-Angeboten** (REWE, Lidl, ALDI Süd, Kaufland, EDEKA). Der Einkaufszettel rechnet in **kaufbaren Packungen** und lässt Vorräte weg.

Angebote kommen aus `backend/data/deals.json` mit einem KW-Label (z. B. `2026-W36`) — kein Live-Scraping.

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

(PowerShell: `$env:PYTHONPATH = "."`)

Terminal 2:

```bash
cd frontend
npm install
npm run dev
```

App: http://127.0.0.1:5173

Standard-Admin (änderbar über Env):

- `ADMIN_EMAIL` (default `admin@localhost`)
- `ADMIN_PASSWORD` (default `changeme-now`)

`python -m backend.seed` legt den Admin an und druckt Einladungscodes.

## Docker

```bash
docker compose up --build
```

Dann http://127.0.0.1:8000 — zuerst einloggen, unter **Einladungen** Codes erzeugen.

Setze in Produktion unbedingt `SECRET_KEY` und ein eigenes Admin-Passwort.

## Freemium / Pro

- **Free:** Wochenplan, Tausch, Fixieren, Ausschlüsse, Einkaufszettel, Vorrats-Häkchen im Setup.
- **Pro (4,99 €/Monat):** persistenter Vorratsschrank + Kassenbon-Scan. Der Admin schaltet Konten unter Admin → Pro frei.
- Kassenbon-OCR braucht `XAI_API_KEY` (SpaceXAI / xAI, Modell grok-4.6).

Admin: **Angebote** = KW-Deals in zehn Minuten aktualisieren. **Admin** = Einladungen, Passwort zurücksetzen, Pro-Toggle.

## Tests

```bash
python -m pytest tests/ -v
```
