# NutriMatch DE 🍃

> **Smarter Wocheneinkauf nach deutschen Supermarkt-Angeboten & Zero Food Waste**

NutriMatch ist eine moderne Web-Applikation, die gesunde, makro-optimierte Wochen-Ernährungspläne (High-Protein, Vegan, Vegetarisch, Low-Carb etc.) mit den **aktuellen Prospekt-Angeboten deutscher Supermärkte** (REWE, Lidl, ALDI Süd, Kaufland, EDEKA) abgleicht. Durch einen **digitalen Vorratsschrank** werden vorhandene Lebensmittel automatisch angerechnet, um Lebensmittelverschwendung zu vermeiden und den wöchentlichen Kassenbon drastisch zu senken.

---

## 🌟 Highlights

- **3-Schritte-Konfigurator:** Fokussierte Kacheln für Supermarkt, Ernährungsziel & Wochenbudget sowie Vorratsschrank.
- **Wochen-Deals („Prospekt-Knaller“):** Automatische Priorisierung rabattierter Produkte mit Kennzeichnung der Ersparnis.
- **Makro-Feintuning:** Individuelle Schieberegler für **Tageskalorien** (kcal) und **Tagesprotein** (g) mit Soll/Ist-Vergleich im Wochenplan.
- **Zero Food Waste (Digitaler Vorratsschrank):** Vorhandene Grundzutaten (z.B. Olivenöl, Reis, Haferflocken) werden vom Kassenpreis abgezogen.
- **Ruhiges Wochenplan-Dashboard:** Klare Wochentags-Ansicht (Mo–So) mit 3 vollwertigen Mahlzeiten (Frühstück, Mittag, Abend) und 1-Klick-Rezept-Tausch.
- **Smarter Einkaufszettel:** Sortiert nach deutschen Supermarkt-Gängen (*Obst & Gemüse, Kühlregal, Fleisch/Alternativen, Trockensortiment*) mit bequemen Checkboxen und WhatsApp-Export.
- **Senior Minimalist Design:** Warmes Stein-Design (`#FBFBFA`), feine Hairline-Borders und dezente Vektor-Iconography.

---

## 🛠️ Tech Stack

- **Backend:** Python 3, Flask, In-Memory Session Cache
- **Frontend:** HTML5, Jinja2 Templates, Tailwind CSS, Lucide Vector Icons
- **Data Layer:** JSON-basierte Preismatrizen und Angebote deutscher Supermärkte

---

## 🚀 Schnellstart

### 1. Repository klonen
```bash
git clone https://github.com/<dein-user>/meal_planner_mvp.git
cd meal_planner_mvp
```

### 2. Abhängigkeiten installieren
```bash
pip install -r requirements.txt
```

### 3. Server starten
```bash
python app.py
```

Die App ist nun erreichbar unter: **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 📂 Projektstruktur

```
meal_planner_mvp/
├── app.py                # Flask Backend & Routing
├── algorithm.py          # Smarter Optimierungs- und Matchmaking-Algorithmus
├── requirements.txt      # Python Abhängigkeiten
├── .gitignore
├── data/
│   ├── deals.json        # Aktuelle Wochen-Angebote je Supermarkt
│   ├── prices.json       # Grundpreismatrix der Märkte
│   └── recipes.json      # Nährwert- und makrooptimierte Rezeptdatenbank
└── templates/
    ├── layout.html       # Minimalistisches Basis-Layout & Header
    ├── setup.html        # Konfigurator-Kacheln (Markt, Ziel/Makros, Vorrat)
    ├── plan.html         # Wochenplan-Dashboard mit Tages-Tabs & Tauschfunktion
    └── einkaufszettel.html# Nach Gängen sortierte Einkaufs-Checkliste
```
