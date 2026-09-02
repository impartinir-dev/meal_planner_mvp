from backend.extensions import db
from backend.kitchen.models import FrozenPack


def render_markdown(match, revision=None):
    rev = f" · Rev {revision}" if revision is not None else ""
    stale = " · stale prices" if match.get("stale") else ""
    lines = [
        f"# NutriMatch · {match['store']} · {match['week']}{rev}{stale}",
        "",
        f"Budget {match['budget']:.2f} € · Kasse {match['total_cost']:.2f} € · "
        f"Angebot −{match['deal_savings']:.2f} € · Vorrat −{match['pantry_savings']:.2f} €",
        "",
    ]
    if match.get("relaxations"):
        lines.append("Relaxations: " + ", ".join(match["relaxations"]))
        lines.append("")
    for day in match["days_plan"]:
        lines.append(f"## {day['day_name']}")
        for meal in day["meals"]:
            deal = ""
            if any(line.get("is_deal") for line in meal["lines"]):
                deal = " · Prospekt-Knaller"
            lines.append(
                f"- {meal['slot']}: {meal['title']} ({meal['active_time_minutes']} Min){deal}"
            )
        lines.append("")
    lines.append("## Einkauf")
    for group in match["shopping_list"]["to_buy"]:
        lines.append(f"### {group['aisle']}")
        for item in group["items"]:
            badge = f" · {item['deal_badge']}" if item.get("deal_badge") else ""
            lines.append(
                f"- [ ] {item['name']} × {item['packs']} — {item['cost']:.2f} €{badge}"
            )
        lines.append("")
    if match["shopping_list"]["already_at_home"]:
        lines.append("### Schon im Vorrat")
        for item in match["shopping_list"]["already_at_home"]:
            lines.append(f"- {item['name']} ({item['ingredient_name']})")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def freeze_pack(match):
    week = match["week"]
    store = match["store"]
    last = (
        FrozenPack.query.filter_by(week=week, store=store)
        .order_by(FrozenPack.revision.desc())
        .first()
    )
    revision = 1 if last is None else last.revision + 1
    payload = dict(match)
    payload["revision"] = revision
    row = FrozenPack(
        week=week,
        store=store,
        revision=revision,
        match_json=payload,
        markdown=render_markdown(payload, revision=revision),
    )
    db.session.add(row)
    db.session.flush()
    return row
