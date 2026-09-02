from pathlib import Path

from backend.extensions import db
from backend.kitchen.catalog import current_price
from backend.kitchen.ingest import FIXTURE_DIR, load_prospekt_fixture, promote_batch
from backend.kitchen.models import Offer, Sku
from backend.kitchen.seed import seed_owned_catalog


def test_promote_updates_offer_and_adds_new_sku(app):
    with app.app_context():
        seed_owned_catalog()
        eggs = Sku.query.filter_by(ean="400000000001").one()
        before = current_price(eggs.id).amount_eur
        assert before == 2.19
        batch = load_prospekt_fixture(FIXTURE_DIR / "lidl-2026-W36.json")
        assert batch.status == "pending"
        assert len(batch.items) == 2
        promote_batch(batch.id)
        db.session.commit()
        after = current_price(eggs.id)
        assert after.amount_eur == 1.59
        offer = Offer.query.filter_by(sku_id=eggs.id, is_current=True).one()
        assert offer.week == "2026-W36"
        assert offer.badge == "Prospekt-Knaller"
        paprika = Sku.query.filter_by(ean="400000000099").one()
        assert paprika.store == "lidl"
        assert current_price(paprika.id).amount_eur == 1.49


def test_empty_fixture_does_not_clobber_prices(app):
    with app.app_context():
        seed_owned_catalog()
        eggs = Sku.query.filter_by(ean="400000000001").one()
        before_id = current_price(eggs.id).id
        before_amt = current_price(eggs.id).amount_eur
        batch = load_prospekt_fixture(FIXTURE_DIR / "lidl-empty.json")
        promote_batch(batch.id)
        db.session.commit()
        assert batch.status == "empty"
        after = current_price(eggs.id)
        assert after.id == before_id
        assert after.amount_eur == before_amt
        assert not after.stale
