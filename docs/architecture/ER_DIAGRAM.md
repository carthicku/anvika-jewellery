# Entity Relationship Diagram

Rendered by any Mermaid-capable Markdown viewer (GitHub, VS Code with a Mermaid extension).
Column details are in [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md). Only key columns are shown.

## Identity, catalogue and pricing

```mermaid
erDiagram
    USERS ||--o{ USER_SESSIONS : "signs in with"
    USERS ||--o{ USER_TOKENS : "verifies / resets with"
    USERS ||--o{ ADDRESSES : owns
    USERS ||--o{ WISHLIST_ITEMS : saves
    USERS ||--o{ PRODUCT_REVIEWS : writes

    CATEGORIES ||--o{ CATEGORIES : "parent of"
    CATEGORIES ||--o{ PRODUCTS : contains
    COLLECTIONS ||--o{ COLLECTION_PRODUCTS : groups
    PRODUCTS ||--o{ COLLECTION_PRODUCTS : "belongs to"
    PRODUCTS ||--|{ PRODUCT_VARIANTS : "sold as"
    PRODUCTS ||--o{ PRODUCT_IMAGES : "shown by"
    PRODUCTS ||--o{ PRODUCT_ATTRIBUTES : "described by"
    PRODUCTS ||--o{ PRODUCT_REVIEWS : receives
    PRODUCTS ||--o{ WISHLIST_ITEMS : "saved as"
    PRODUCT_VARIANTS ||--|| INVENTORY_LEVELS : "stocked as"
    PRODUCT_VARIANTS ||--o{ INVENTORY_MOVEMENTS : "changed by"
    GOLD_RATES }o--|| USERS : "entered by"

    USERS {
        uuid id PK
        string email UK
        string role
        bool is_active
    }
    PRODUCTS {
        uuid id PK
        string slug UK
        string purity
        string pricing_model
        string making_charge_type
        numeric making_charge_value
        string status
    }
    PRODUCT_VARIANTS {
        uuid id PK
        uuid product_id FK
        string sku UK
        numeric net_gold_weight_g
        numeric fixed_price
    }
    INVENTORY_LEVELS {
        uuid variant_id PK
        int on_hand
        int reserved
    }
    GOLD_RATES {
        uuid id PK
        string purity
        numeric rate_per_gram
        timestamptz effective_from
    }
```

## Cart, checkout, orders and payments

```mermaid
erDiagram
    USERS ||--o{ CARTS : has
    CARTS ||--o{ CART_ITEMS : contains
    PRODUCT_VARIANTS ||--o{ CART_ITEMS : "added as"

    USERS |o--o{ ORDERS : places
    ORDERS ||--|{ ORDER_ITEMS : contains
    ORDERS ||--o{ ORDER_EVENTS : "history"
    ORDERS ||--o{ INVENTORY_RESERVATIONS : holds
    PRODUCT_VARIANTS ||--o{ INVENTORY_RESERVATIONS : "reserved in"
    ORDERS ||--o{ PAYMENT_ATTEMPTS : "paid via"
    ORDERS ||--o{ REFUNDS : "refunded by"
    PAYMENT_ATTEMPTS ||--o{ REFUNDS : "refunded from"
    ORDERS ||--o{ SHIPMENTS : "shipped as"
    ORDERS ||--o{ RETURN_REQUESTS : "returned via"
    COUPONS ||--o{ COUPON_REDEMPTIONS : "used in"
    ORDERS ||--o| COUPON_REDEMPTIONS : uses

    ORDERS {
        uuid id PK
        string reference UK
        string status
        string payment_status
        numeric grand_total
        string idempotency_key UK
        timestamptz payment_expires_at
    }
    ORDER_ITEMS {
        uuid id PK
        uuid order_id FK
        string sku
        numeric unit_price
        numeric line_total
        jsonb price_inputs
    }
    PAYMENT_ATTEMPTS {
        uuid id PK
        uuid order_id FK
        string provider_order_id UK
        string provider_payment_id UK
        bigint amount_paise
        string status
    }
    PAYMENT_EVENTS {
        uuid id PK
        string event_id UK
        string event_type
        timestamptz processed_at
    }
```

`PAYMENT_EVENTS` is linked to payment attempts through the provider ids inside its payload, not
through a foreign key. That way a webhook for an unknown order can still be stored and
investigated.
