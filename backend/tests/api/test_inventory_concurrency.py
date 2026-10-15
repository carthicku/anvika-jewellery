"""Two checkouts racing for the last piece, on two real database connections at the same time.

Other tests share one rolled-back transaction, which cannot show locking. This test commits its
own small product to the TEST database and deletes it again afterwards.
"""

from __future__ import annotations

import threading
import uuid
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import Engine, delete, select
from sqlalchemy.orm import Session

from app.core.errors import OutOfStock
from app.core.time import utcnow
from app.models import (
    Category,
    InventoryLevel,
    InventoryMovement,
    Order,
    Product,
    ProductVariant,
)
from app.services import inventory


def _make_order(db: Session, tag: str) -> uuid.UUID:
    now = utcnow()
    order = Order(
        reference=f"TST-{tag}-{uuid.uuid4().hex[:6].upper()}",
        email="race@example.com",
        phone="+919876543210",
        customer_name="Race Test",
        subtotal=Decimal("1.00"),
        automatic_discount=Decimal("0.00"),
        coupon_discount=Decimal("0.00"),
        taxable_total=Decimal("1.00"),
        tax_total=Decimal("0.00"),
        shipping_total=Decimal("0.00"),
        rounding_adjustment=Decimal("0.00"),
        grand_total=Decimal("1.00"),
        shipping_address={},
        billing_address={},
        shipping_method={},
        pricing_context={},
        idempotency_key=uuid.uuid4().hex,
        terms_accepted_at=now,
        payment_expires_at=now + timedelta(minutes=30),
    )
    db.add(order)
    db.flush()
    return order.id


def test_only_one_of_two_simultaneous_checkouts_gets_the_last_piece(engine: Engine) -> None:
    with Session(engine) as setup:
        category = setup.scalar(select(Category).limit(1))
        assert category is not None
        product = Product(
            name="Concurrency test piece",
            slug=f"concurrency-test-{uuid.uuid4().hex[:8]}",
            category_id=category.id,
            status="draft",
            pricing_model="fixed",
            purity="22K",
            making_charge_type="none",
            making_charge_value=Decimal("0"),
            is_sample=True,
        )
        setup.add(product)
        setup.flush()
        variant = ProductVariant(
            product_id=product.id,
            sku=f"TST-{uuid.uuid4().hex[:8].upper()}",
            label="One size",
            fixed_price=Decimal("1000.00"),
        )
        setup.add(variant)
        setup.flush()
        inventory.set_initial_stock(setup, variant.id, 1)
        setup.commit()
        product_id, variant_id = product.id, variant.id

    barrier = threading.Barrier(2)
    results: list[str] = []
    lock = threading.Lock()

    def buyer(tag: str) -> None:
        with Session(engine) as db:
            order_id = _make_order(db, tag)
            barrier.wait()  # both transactions are open; now race for the stock row
            try:
                inventory.reserve(db, order_id, [(variant_id, 1)], utcnow() + timedelta(minutes=30))
                db.commit()
                outcome = "reserved"
            except OutOfStock:
                db.rollback()
                outcome = "out_of_stock"
            with lock:
                results.append(outcome)

    threads = [threading.Thread(target=buyer, args=(tag,)) for tag in ("A", "B")]
    try:
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        assert sorted(results) == ["out_of_stock", "reserved"]
        with Session(engine) as check:
            level = check.get(InventoryLevel, variant_id)
            assert level is not None
            assert (level.on_hand, level.reserved) == (1, 1)
    finally:
        with Session(engine) as cleanup:
            # Deleting the orders also deletes their reservations (ON DELETE CASCADE).
            cleanup.execute(delete(Order).where(Order.reference.like("TST-%")))
            cleanup.execute(
                delete(InventoryMovement).where(InventoryMovement.variant_id == variant_id)
            )
            cleanup.execute(delete(Product).where(Product.id == product_id))
            cleanup.commit()
