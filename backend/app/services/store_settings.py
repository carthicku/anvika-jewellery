"""Owner-editable store settings (stored in `store_settings`, edited in Admin → Settings).

Each group has defaults here; stored values override them key by key. Business facts that the
owner has not provided yet are explicit placeholders (docs/ASSUMPTIONS_AND_DECISIONS.md §1).
"""

from __future__ import annotations

import copy
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import StoreSetting
from app.services.pricing import TaxRates

PLACEHOLDER = "[To be configured]"

DEFAULTS: dict[str, dict[str, Any]] = {
    "store": {
        "tagline": "Fine gold jewellery",
        "support_email": "[Support email — to be configured]",
        "support_phone": "[Support phone — to be configured]",
        "whatsapp": None,
        "business_address": "[Business address — to be configured]",
        "gstin": "[GSTIN — to be configured]",
        "business_hours": "[Business hours — to be configured]",
    },
    "announcement": {"enabled": False, "text": "", "link": None},
    # Placeholder GST rates (ASSUMPTIONS P3) — must be confirmed by a tax professional.
    "tax": {
        "metal_percent": "3.00",
        "making_percent": "3.00",
        "stones_percent": "3.00",
        "shipping_percent": "0.00",
    },
    "pricing_policy": {
        "gold_rate_max_change_percent": "5.00",
        "gold_rate_stale_after_hours": 36,
        "block_checkout_when_rate_stale": False,
    },
}


def get_group(db: Session, key: str) -> dict[str, Any]:
    """Defaults merged with any stored overrides for one settings group."""
    if key not in DEFAULTS:
        raise KeyError(f"Unknown settings group {key!r}")
    merged = copy.deepcopy(DEFAULTS[key])
    stored = db.execute(select(StoreSetting.value).where(StoreSetting.key == key)).scalar()
    if isinstance(stored, dict):
        merged.update({k: v for k, v in stored.items() if k in merged})
    return merged


def get_tax_rates(db: Session) -> TaxRates:
    tax = get_group(db, "tax")
    return TaxRates(
        metal=Decimal(str(tax["metal_percent"])),
        making=Decimal(str(tax["making_percent"])),
        stones=Decimal(str(tax["stones_percent"])),
        shipping=Decimal(str(tax["shipping_percent"])),
    )


def set_group(db: Session, key: str, values: dict[str, Any], updated_by: Any = None) -> None:
    """Store overrides for a group (unknown keys are ignored). Caller commits and audits."""
    current = get_group(db, key)
    current.update({k: v for k, v in values.items() if k in DEFAULTS[key]})
    row = db.get(StoreSetting, key)
    if row is None:
        db.add(StoreSetting(key=key, value=current, updated_by=updated_by))
    else:
        row.value = current
        row.updated_by = updated_by
