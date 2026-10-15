"""Gold rate administration (docs/architecture/PRICING_ENGINE.md §7).

Rates are append-only and entered by the owner from a source they choose (no live feed, no
hard-coded market rate). Before saving, the admin sees how every affected price changes; a change
larger than `gold_rate_max_change_percent` must be confirmed explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import Conflict
from app.core.money import money
from app.core.time import utcnow
from app.models import GoldRate, Product, User
from app.services import audit, store_settings
from app.services.catalogue import refresh_price_cache
from app.services.pricing import PriceUnavailable
from app.services.pricing_context import current_gold_rates, load_pricing_context

PURITIES = ("24K", "22K", "18K", "14K")
HUNDRED = Decimal(100)


@dataclass
class RateStatus:
    purity: str
    rate: GoldRate | None
    age_hours: Decimal | None
    stale: bool


def policy(db: Session) -> tuple[Decimal, int]:
    group = store_settings.get_group(db, "pricing_policy")
    return Decimal(str(group["gold_rate_max_change_percent"])), int(
        group["gold_rate_stale_after_hours"]
    )


def current_status(db: Session, now: datetime | None = None) -> list[RateStatus]:
    now = now or utcnow()
    rates = current_gold_rates(db, now)
    _, stale_after = policy(db)
    out = []
    for purity in PURITIES:
        rate = rates.get(purity)
        age = (
            Decimal((now - rate.effective_from).total_seconds() / 3600).quantize(Decimal("0.1"))
            if rate
            else None
        )
        out.append(RateStatus(purity, rate, age, bool(age is not None and age > stale_after)))
    return out


def history(db: Session, limit: int = 100) -> list[GoldRate]:
    return list(
        db.scalars(
            select(GoldRate)
            .order_by(GoldRate.effective_from.desc(), GoldRate.created_at.desc())
            .limit(limit)
        ).all()
    )


@dataclass
class PriceImpact:
    product_name: str
    product_slug: str
    sku: str
    variant_label: str
    old_price: Decimal | None
    new_price: Decimal


@dataclass
class RatePreview:
    purity: str
    current_rate: Decimal | None
    new_rate: Decimal
    change_percent: Decimal | None
    needs_confirmation: bool
    max_change_percent: Decimal
    impacts: list[PriceImpact]


def preview(db: Session, purity: str, new_rate: Decimal) -> RatePreview:
    """Old vs new price of every active weight-based piece of this purity. Changes nothing."""
    if purity not in PURITIES:
        raise ValueError("Unknown purity")
    new_rate = money(new_rate)
    max_change, _ = policy(db)
    products = list(
        db.scalars(
            select(Product)
            .where(
                Product.purity == purity,
                Product.pricing_model == "weight_based",
                Product.status == "active",
            )
            .options(selectinload(Product.variants))
            .order_by(Product.name)
        ).all()
    )
    ctx = load_pricing_context(db, products)
    current = ctx.rates.get(purity)
    current_rate = current.rate_per_gram if current else None
    change = (
        ((new_rate - current_rate) / current_rate * HUNDRED).quantize(Decimal("0.01"))
        if current_rate
        else None
    )
    impacts: list[PriceImpact] = []
    for product in products:
        for variant in product.variants:
            if not variant.is_active:
                continue
            try:
                old = ctx.price(product, variant).total
            except PriceUnavailable:
                old = None
            hypothetical = GoldRate(
                id=None,
                purity=purity,
                rate_per_gram=new_rate,
                effective_from=utcnow(),
                source_note="preview",
            )
            ctx.rates[purity] = hypothetical
            try:
                new = ctx.price(product, variant).total
            finally:
                if current is not None:
                    ctx.rates[purity] = current
                else:
                    del ctx.rates[purity]
            impacts.append(
                PriceImpact(product.name, product.slug, variant.sku, variant.label, old, new)
            )
    return RatePreview(
        purity=purity,
        current_rate=current_rate,
        new_rate=new_rate,
        change_percent=change,
        needs_confirmation=change is not None and abs(change) > max_change,
        max_change_percent=max_change,
        impacts=impacts,
    )


def create_rate(
    db: Session,
    actor: User,
    *,
    purity: str,
    rate_per_gram: Decimal,
    source_note: str,
    effective_from: datetime | None,
    confirm_large_change: bool,
    ip_address: str | None = None,
) -> GoldRate:
    """Append a new rate (caller commits). Refreshes the listing price cache."""
    result = preview(db, purity, rate_per_gram)
    if result.needs_confirmation and not confirm_large_change:
        raise Conflict(
            f"This changes the {purity} rate by {result.change_percent}% — more than the "
            f"{result.max_change_percent}% safety limit. Please confirm the change.",
            code="LARGE_RATE_CHANGE",
            details={
                "change_percent": str(result.change_percent),
                "max_change_percent": str(result.max_change_percent),
            },
        )
    now = utcnow()
    when = effective_from or now
    rate = GoldRate(
        purity=purity,
        rate_per_gram=result.new_rate,
        effective_from=when,
        source_note=source_note.strip(),
        created_by=actor.id,
    )
    db.add(rate)
    db.flush()
    audit.record(
        db,
        actor=actor,
        action="gold_rate.create",
        entity_type="gold_rate",
        entity_id=rate.id,
        changes={
            "purity": purity,
            "previous": str(result.current_rate) if result.current_rate else None,
            "new": str(result.new_rate),
            "change_percent": str(result.change_percent) if result.change_percent else None,
            "effective_from": when.isoformat(),
            "source_note": rate.source_note,
            "confirmed_large_change": result.needs_confirmation,
        },
        ip_address=ip_address,
    )
    if when <= now:
        refresh_price_cache(db)
    return rate
