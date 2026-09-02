# Kitchen OS Implementation Plan

**Goal:** Make Kitchen OS the source of truth (ingredients, SKUs, prices, owned recipes, mappings, matcher, packs) and put NutriMatch on that API with an honest Lidl/Marktkauf picker.

**Architecture:** One Flask service. New `backend/kitchen/` package owns catalog + ingest + match. Existing JSON planner stays until the matcher has golden tests, then NutriMatch switches. Postgres later; SQLite now/tests.

**Tech stack:** Flask, SQLAlchemy, PuLP, pytest, existing React client.

**Contract:** `docs/KITCHEN-OS.md`

---

### Task 1: Catalog schema + shoppable rule

**Files:**
- Create: `backend/kitchen/__init__.py`, `models.py`, `constants.py`, `catalog.py`, `shoppable.py`
- Create: `tests/test_kitchen_catalog.py`
- Modify: `backend/__init__.py` (import kitchen models so `create_all` runs)

**Done when:**
- Ingredient, Sku, PriceObservation, Offer, Recipe, RecipeLine, IngredientSku persist
- Recipe lines reference ingredients, never SKUs
- `record_price` with `None` does not clobber current
- Published recipe is shoppable at a store iff every line is mapped
- Unmapped ingredient → not shoppable
- `active_time_minutes <= 10` is the 10-minute lane
- `pytest tests/test_kitchen_catalog.py tests/` green (old suite still passes)

### Task 2: Admin catalog API

**Files:** `backend/kitchen/api.py`, `tests/test_kitchen_api.py`, register blueprint `/api/kitchen`

Admin CRUD: ingredients, recipes (draft/tested/published), IngredientSku maps. Public/read for published recipes + current prices. Drafts hidden from non-admin.

### Task 3: Owned seed + frozen weeks

Small **house** catalog (not a dump of `recipes.json`): ≥1 sub-10-minute recipe, ≥1 international dish, Lidl + Marktkauf SKUs/offers as fixtures under `backend/kitchen/fixtures/`.

### Task 4: Ingest review batch

Adapters parse **saved** Prospekt fixtures only. Write pending batch; promote makes observations current; empty parse does not overwrite.

### Task 5: Matcher + pack

ILP over published + shoppable recipes. Pantry quantities, pack-size list, named relaxations, freeze pack revision. Golden tests from Task 3 fixtures.

### Task 6: NutriMatch client honesty

`/api/meta` stores = stores with current observations (`lidl`, `marktkauf`). Setup/plan/swap/shopping/pantry call Kitchen OS. Stone UI kept. Old JSON path removed only after green.

---

Do not scrape live stores in CI. Do not publish unmapped recipes. Do not show REWE until it has current prices.
