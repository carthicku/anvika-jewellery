"""All SQLAlchemy models. Importing this package registers every table on `Base.metadata`
(Alembic autogenerate and the test fixtures rely on that)."""

from app.models.base import Base
from app.models.cart import Cart, CartItem, Coupon, CouponRedemption
from app.models.catalogue import (
    Category,
    Collection,
    CollectionProduct,
    Product,
    ProductAttribute,
    ProductImage,
    ProductReview,
    ProductVariant,
)
from app.models.content import ContactEnquiry, ContentPage, NewsletterSubscriber
from app.models.email import EmailOutbox
from app.models.identity import Address, User, UserSession, UserToken, WishlistItem
from app.models.inventory import InventoryLevel, InventoryMovement
from app.models.orders import (
    InventoryReservation,
    Order,
    OrderEvent,
    OrderItem,
    PaymentAttempt,
    PaymentEvent,
    Refund,
    ReturnRequest,
    Shipment,
)
from app.models.pricing import Discount, GoldRate
from app.models.shipping import ShippingMethod, ShippingZone
from app.models.system import AuditLog, RateLimitBucket, StoreSetting

__all__ = [
    "Address",
    "AuditLog",
    "Base",
    "Cart",
    "CartItem",
    "Category",
    "Collection",
    "CollectionProduct",
    "ContactEnquiry",
    "ContentPage",
    "Coupon",
    "CouponRedemption",
    "Discount",
    "EmailOutbox",
    "GoldRate",
    "InventoryLevel",
    "InventoryMovement",
    "InventoryReservation",
    "NewsletterSubscriber",
    "Order",
    "OrderEvent",
    "OrderItem",
    "PaymentAttempt",
    "PaymentEvent",
    "Product",
    "ProductAttribute",
    "ProductImage",
    "ProductReview",
    "ProductVariant",
    "RateLimitBucket",
    "Refund",
    "ReturnRequest",
    "Shipment",
    "ShippingMethod",
    "ShippingZone",
    "StoreSetting",
    "User",
    "UserSession",
    "UserToken",
    "WishlistItem",
]
