"""Allowed values for enum-like VARCHAR columns (enforced by CHECK constraints)."""

from __future__ import annotations

PRODUCT_STATUSES = ("draft", "active", "archived")
PURITIES = ("24K", "22K", "18K", "14K")
METAL_COLOURS = ("yellow", "white", "rose", "two_tone")
PRICING_MODELS = ("fixed", "weight_based")
MAKING_CHARGE_TYPES = ("per_gram", "percent", "flat", "none")

DISCOUNT_KINDS = ("percent_off_making", "percent_off_price", "flat_off_price")
DISCOUNT_SCOPES = ("all", "category", "collection", "product")

INVENTORY_REASONS = (
    "initial",
    "adjustment",
    "reservation",
    "reservation_release",
    "sale",
    "cancellation_restock",
    "return_restock",
)

ENQUIRY_STATUSES = ("new", "in_progress", "closed")
SUBSCRIBER_STATUSES = ("subscribed", "unsubscribed")
