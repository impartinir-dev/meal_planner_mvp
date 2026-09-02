from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from backend.algorithm import PACK_SIZES, nice_quantity, pack_info
from backend.extensions import db
from backend.models import CupboardItem
from backend.ocr import scan_receipt_image

cupboard_bp = Blueprint("cupboard", __name__)


def _require_pro():
    if not current_user.has_pro():
        return jsonify({"error": "pro_required"}), 402
    return None


def _item_json(item):
    return {
        "id": item.id,
        "name": item.name,
        "quantity": nice_quantity(item.quantity, item.unit),
        "unit": item.unit,
        "source": item.source,
    }


@cupboard_bp.get("/")
@login_required
def list_cupboard():
    denied = _require_pro()
    if denied:
        return denied
    items = CupboardItem.query.filter_by(user_id=current_user.id).order_by(CupboardItem.name).all()
    return jsonify({"items": [_item_json(i) for i in items]})


@cupboard_bp.post("/")
@login_required
def add_cupboard():
    denied = _require_pro()
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    name = str(data.get("name") or "").strip()
    if name not in PACK_SIZES:
        return jsonify({"error": "unknown_ingredient"}), 400
    _, unit, _ = pack_info(name)
    try:
        qty = float(data.get("quantity") or 0)
    except (TypeError, ValueError):
        return jsonify({"error": "invalid_quantity"}), 400
    qty = nice_quantity(qty, data.get("unit") or unit)
    existing = CupboardItem.query.filter_by(user_id=current_user.id, name=name).first()
    if existing:
        existing.quantity = (existing.quantity or 0) + qty
        existing.unit = unit
        db.session.commit()
        return jsonify(_item_json(existing)), 200
    item = CupboardItem(
        user_id=current_user.id,
        name=name,
        quantity=qty,
        unit=unit,
        source=str(data.get("source") or "manual"),
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(_item_json(item)), 201


@cupboard_bp.delete("/<int:item_id>")
@login_required
def delete_cupboard(item_id):
    denied = _require_pro()
    if denied:
        return denied
    item = CupboardItem.query.filter_by(id=item_id, user_id=current_user.id).first()
    if item is None:
        return jsonify({"error": "not_found"}), 404
    db.session.delete(item)
    db.session.commit()
    return ("", 204)


@cupboard_bp.post("/scan")
@login_required
def scan_receipt():
    denied = _require_pro()
    if denied:
        return denied
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        return jsonify({"error": "missing_file"}), 400
    mime = upload.mimetype or "image/jpeg"
    if mime not in ("image/jpeg", "image/jpg", "image/png"):
        return jsonify({"error": "unsupported_type"}), 400
    raw = upload.read()
    if not raw or len(raw) > 20 * 1024 * 1024:
        return jsonify({"error": "invalid_file"}), 400
    try:
        parsed = scan_receipt_image(raw, mime=mime, ingredient_names=list(PACK_SIZES.keys()))
    except RuntimeError as exc:
        if str(exc) == "ocr_not_configured":
            return jsonify({"error": "ocr_not_configured"}), 503
        return jsonify({"error": "ocr_failed"}), 502
    except Exception:
        return jsonify({"error": "ocr_failed"}), 502

    added = []
    for row in parsed:
        name = row["name"]
        unit = row.get("unit") or pack_info(name)[1]
        qty = nice_quantity(row["quantity"], unit)
        existing = CupboardItem.query.filter_by(user_id=current_user.id, name=name).first()
        if existing:
            existing.quantity = (existing.quantity or 0) + qty
            existing.source = "receipt"
            db.session.add(existing)
            added.append(existing)
        else:
            item = CupboardItem(
                user_id=current_user.id,
                name=name,
                quantity=qty,
                unit=unit,
                source="receipt",
            )
            db.session.add(item)
            added.append(item)
    db.session.commit()
    return jsonify({"items": [_item_json(i) for i in added], "count": len(added)})
