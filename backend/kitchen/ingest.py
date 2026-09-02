import json
from pathlib import Path

from backend.extensions import db
from backend.kitchen.catalog import CatalogError, create_sku, record_offer, record_price
from backend.kitchen.constants import STORES
from backend.kitchen.models import IngestBatch, IngestItem, Sku


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def _find_sku(store, ean, name):
    if ean:
        found = Sku.query.filter_by(store=store, ean=ean).one_or_none()
        if found:
            return found
    return Sku.query.filter_by(store=store, name=name).one_or_none()


def load_prospekt_fixture(path):
    path = Path(path)
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    store = data.get("store")
    week = data.get("week")
    if store not in STORES:
        raise CatalogError(f"unknown store: {store}")
    if not week:
        raise CatalogError("week is required")
    items = data.get("items") or []
    batch = IngestBatch(store=store, week=week, source=path.name, status="pending")
    db.session.add(batch)
    db.session.flush()
    for raw in items:
        amount = raw.get("price")
        offer = raw.get("offer_price")
        if amount is None and offer is None:
            continue
        db.session.add(
            IngestItem(
                batch_id=batch.id,
                name=raw["name"],
                brand=raw.get("brand"),
                ean=raw.get("ean"),
                pack_size=float(raw["pack_size"]),
                pack_unit=raw["pack_unit"],
                aisle=raw.get("aisle") or "Sonstiges",
                amount_eur=None if amount is None else float(amount),
                offer_price=None if offer is None else float(offer),
                regular_price=None if raw.get("regular_price") is None else float(raw["regular_price"]),
                badge=raw.get("badge"),
                status="pending",
            )
        )
    db.session.flush()
    return batch


def promote_batch(batch_id):
    batch = db.session.get(IngestBatch, batch_id)
    if batch is None:
        raise CatalogError("unknown batch")
    if batch.status == "promoted":
        return batch
    items = IngestItem.query.filter_by(batch_id=batch.id, status="pending").all()
    if not items:
        batch.status = "empty"
        db.session.flush()
        return batch
    for item in items:
        sku = _find_sku(batch.store, item.ean, item.name)
        if sku is None:
            sku = create_sku(
                batch.store,
                item.name,
                item.pack_size,
                item.pack_unit,
                aisle=item.aisle,
                brand=item.brand,
                ean=item.ean,
            )
        price = item.offer_price if item.offer_price is not None else item.amount_eur
        if price is None:
            item.status = "skipped"
            continue
        record_price(sku.id, price, source=batch.source)
        if item.offer_price is not None:
            record_offer(
                sku.id,
                batch.week,
                item.offer_price,
                regular_price=item.regular_price or item.amount_eur,
                badge=item.badge,
                source=batch.source,
            )
        item.sku_id = sku.id
        item.status = "accepted"
    batch.status = "promoted"
    db.session.flush()
    return batch
