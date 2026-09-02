# Kitchen OS + NutriMatch

Working name for the engine: **Kitchen OS**.  
Consumer product: **NutriMatch**.

This is the product contract. JSON catalogs and the current Flask planner are a prototype of the matcher idea, not the source of truth going forward.

---

## Understanding

- We are building a **kitchen IP**, not another planner-first app. The durable asset is owned recipes × supermarket prices/Angebote × a matcher.
- **NutriMatch** is the first consumer client: a German web app that turns that engine into a weekly plan, Prospekt-Knaller, pantry-aware Kassenbon, and aisle shopping list.
- First cooks: busy, household shop, budget, health-conscious — one person, not four products.
- First live stores: **Lidl** and **Marktkauf** (the shops we actually use). REWE, ALDI Süd, Kaufland, EDEKA are the public roadmap, not fake picker options.
- v1 build order: Kitchen OS (API + admin + weekly pack) until a match is *true* for Lidl and Marktkauf → then NutriMatch on that API. An appliance, if ever, is another client of the same API.

## Assumptions

- Market is Germany. UI is German. Recipe *cuisine* is international. Recipe *text* may be DE or EN.
- Portions default to a small household (2–4). Nutrition is real (kcal, protein, allergens) and not medical advice.
- Sub-10-minute means **active** cook time ≤ 10 minutes.
- Automation: public Prospekt/offer pages and any official or licensed shelf data. If a source blocks us, admin still works. Last good price stays. We never invent a price. A stealth scraper is not the product.
- Operator scale: hundreds of recipes, thousands of SKUs, two stores. Postgres in the service; SQLite in tests. JSON is fixtures/export only.
- One store per match in v1 (Lidl *or* Marktkauf). Pantry is store-agnostic. Split basket is later.

## Non-goals (v1)

- Consumer app on invented 5-store prices
- Aggregating other sites’ recipe text
- Stealth scraping as the catalog
- Split shopping trip across stores
- PDF pack, receipt OCR, Pro paywall (unless reintroduced later)
- Hardware / appliances
- Marketplace, social, user-generated recipes

## Decision log

| Decision | Alternatives | Why |
| --- | --- | --- |
| IP is the stack: recipes + prices + matcher | Wedge on only prices or only recipes | All three are the product; construction order is OS then client |
| First stores: Lidl + Marktkauf | REWE-only; five chains day one | Honest graph for shops we use; five-chain copy is roadmap |
| Recipe IP: house-authored + rewritten tested classics | License; scrape Chefkoch et al. | We own the text; dish names can be classic |
| Cuisine: international | German-only kitchen | Pad Thai is allowed if it maps to a DE SKU or a flagged substitute |
| v1 surface: API + admin + weekly pack, then NutriMatch | App-first; cookbook-only; price-graph-only | App is a client; OS must be true first |
| NutriMatch keeps the name and stone UI | Rename the consumer app | Copy and design are the product face; OS is unnamed internally |
| Digital Vorratsschrank is core | Pro-only pantry | Zero-waste / Kassenbon is in the consumer contract |
| One store per match | Split Lidl+Marktkauf basket | Matches the 3-step “Supermarkt” configurator |
| Prices: automate Angebote + as much shelf as we can, with review | Full manual; stealth scrape | Review batch keeps the catalog honest |
| Postgres (SQLite for tests) | JSON files as truth | History, review, frozen packs need a real store |

---

## Domain (the IP)

### Ingredient

Kitchen word, not a shelf. Canonical id, aliases (DE/EN/…), default unit, conversions. “Fish sauce” and *Fischsauce* are the same row.

### SKU

Buyable item at a **store** (`lidl` \| `marktkauf` \| later others). Printed name, brand, EAN if known, pack size, pack unit, aisle.

A **price observation**: `amount`, `observed_at`, `source`, `confidence`.  
An **Offer**: dated observation with a week window (Prospekt).  
Failed ingest → keep last good row, mark `stale`. Never invent a price. Never delete a SKU because a page 404’d once.

### Recipe

Owned IP. Our title, our steps, our yields. Any cuisine. `locale` is a field. `active_time_minutes` is the 10-minute gate. Lines point at **ingredients**, never at SKUs. Status: `draft → tested → published`. Drafts do not ship in a pack or in NutriMatch.

### IngredientSKU (honesty layer)

`ingredient` + `store` + `sku` + optional substitute flag + yield factor.  
Unmapped published recipe = **not shoppable** at that store-week. Matcher skips it. No silent guess.

### Generated (not IP)

- **Match** — week, store, household, budget, diet/macros, pantry, time filter → slots + pack-size shopping list + substitutions + named relaxations.
- **Weekly pack** — frozen render of a Match + that week’s Angebote (`2026-W36-lidl`, revisioned). Re-ingest does not silently rewrite a frozen pack.
- **NutriMatch session** — UI state over the API (locks, swaps, slider values, pantry quantities).

Reuse from the prototype: pack-size math, allergen skip, ILP-style assignment, named relaxations.  
Drop as truth: NutriMatch as the engine, REWE-only assumption, static `backend/data/*.json`.

---

## System

One service, four jobs. Not microservices.

1. **Ingest** — Lidl and Marktkauf adapters. Public Angebote, plus shelf prices where the source is usable. Each run writes a **review batch**. Nothing becomes `current` until admin confirms, except explicit trust rules (e.g. same EAN, small price move).
2. **Catalog** — recipes, ingredients, IngredientSKU. Admin-only writes.
3. **Matcher** — read-only over *published* recipes + *current* observations. Output is a Match.
4. **Pack** — JSON + Markdown render of a Match. PDF later.

Auth: admin is authenticated. If a public API exists, it is read-only and never sees drafts.

```
Prospekt week opens
  → ingest both stores
  → review queue
  → confirm → current observations rotate (history kept)
  → match (store, household, budget, macros, pantry, filters)
  → freeze pack revision
```

NutriMatch and any future appliance are clients of the same match/pack API.

---

## NutriMatch (consumer client)

Contract, in product language:

NutriMatch ist eine Web-Applikation, die makro-optimierte Wochenpläne (High-Protein, Vegan, Vegetarisch, Low-Carb, …) mit aktuellen Prospekt-Angeboten abgleicht. Der digitale Vorratsschrank rechnet vorhandene Lebensmittel an, senkt den Kassenbon, vermeidet Verschwendung.

**v1 live stores in the picker:** only stores with current observations (Lidl, Marktkauf). The headline five-chain list is roadmap copy until ingest is real. Marktkauf is in the picker even if it is not in the marketing sentence yet.

Highlights → API:

| UI | Engine |
| --- | --- |
| 3-step configurator: store, diet goal + weekly budget, pantry | Match inputs |
| Prospekt-Knaller + € saved | Offer observations on chosen SKUs |
| kcal / protein sliders + Soll/Ist | Daily targets; per-day sums on the Match |
| Digitaler Vorratsschrank | Pantry *quantities* deducted before pack-size rounding |
| Mo–So, 3 meals, 1-click swap | 7-day match; re-solve one slot, keep locks |
| Einkaufszettel by German aisles, checkboxes, WhatsApp | Pack lines + aisle on SKU |
| Senior minimalist: `#FBFBFA`, hairlines, quiet icons | Existing frontend visual language |

Vorratsschrank is **core**, not a Pro add-on, unless we later reintroduce paywall around something else.

---

## Matcher rules

- One store per Match.
- Pantry is quantity: 200 g on hand vs 500 g needed → buy 300 g, round up to packs, charge packs only. Enough staple → €0 and no line.
- Unmapped ingredient → recipe not a candidate. Flagged *Ersatz* only if IngredientSKU says substitute.
- Stale prices: still match, pack badge `stale`.
- Offers outside their window do not apply.
- Swap: forbid that recipe in that slot; locks hold; if no legal recipe remains, the API says so.
- Macros: daily slider targets; if ILP relaxes budget or macros, return **named** relaxations, never a silent miss.
- 10-minute lane: filter `active_time_minutes <= 10` on published recipes, not a second catalog.

---

## Failure rules

- Empty or failed fetch does not overwrite current prices.
- Unmapped ≠ substitute.
- Frozen pack is immutable; mint a revision.
- Admin required for catalog and for promoting ingest.
- Never show a store in NutriMatch that has no current observations.

## Risks

- Store HTML/PDF layout changes break adapters. Mitigation: saved fixtures + review queue + last-good prices.
- Discounter assortment cannot cover every international recipe. Mitigation: shoppable flag, substitutes, don’t publish unmapped recipes for that store.
- ToS / legal on automated fetch. Mitigation: public advertising (Prospekt) first, licensed shelf data later, no stealth scraper, admin fallback.
- Recipe copyright if “rewrites” stay too close to a source. Mitigation: we author steps and yields; test in a real kitchen before `tested`.

---

## Testing

No live store network in CI.

- Frozen weeks: one Lidl, one Marktkauf.
- International recipes with maps; unmapped-tamarind case.
- Pantry partial-rice case.
- Swap-exhaust case.
- Ingest parsers against **saved** Prospekt HTML/PDF.
- Matcher golden tests: same inputs → same recipe ids and pack lines.
- Price history: empty fetch does not clobber current.

---

## Implementation order (when we build)

1. Schema: Ingredient, SKU, Observation/Offer, Recipe, RecipeLine, IngredientSKU, Match/Pack, admin user.
2. Admin API: CRUD recipes/ingredients/maps; ingest review promote.
3. Seed a small *owned* catalog (including a 10-minute lane) mapped to Lidl + Marktkauf fixtures.
4. Ingest adapters with fixtures; review batch.
5. Matcher + pack renderer (JSON/Markdown) with golden tests.
6. NutriMatch client on the API: setup → plan → swap → shopping list → pantry. Picker = live stores only.

## Open

- Public display name for the engine (internal: Kitchen OS).
- Exact Lidl / Marktkauf ingest URLs and whether a licensed feed appears.
- Invite-only vs open registration for NutriMatch.
