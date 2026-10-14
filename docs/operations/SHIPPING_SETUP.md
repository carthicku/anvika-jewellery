# Shipping Setup

## Current capability (v1)
* **Shipping methods** (Admin → Shipping): name, fee (₹), optional "free above" amount, delivery-day
  range (min–max business days), active flag, display order.
* **Serviceable zones** (optional): lists of PIN-code prefixes (e.g. `56` for much of Karnataka) with
  extra delivery days. If no active zone exists, every valid Indian PIN code is serviceable. If any
  zone exists, only PIN codes matching a zone are serviceable.
* **PIN-code check** on the product page and in checkout: validates the format and shows the
  serviceability and estimated delivery range from these settings. It does **not** look up
  city/state, because no verified PIN-code dataset or API has been chosen (ASSUMPTIONS C4).
* **Tracking**: an admin adds the carrier, tracking number and tracking URL to the order. The
  customer is emailed and sees it in their account.

High-value jewellery shipments usually need insured, signature-on-delivery services. Choose a
partner that supports this, and state it in the shipping policy only once it is true.

## Integrating a courier API later (e.g. Shiprocket, Delhivery, BlueDart)
1. Choose the partner, sign the agreement, and read their current API documentation and terms.
2. Add `app/services/shipping/<partner>.py` implementing the `ShippingProvider` interface:
   `check_serviceability(pincode) -> Serviceability`, `create_shipment(order) -> ShipmentRef`,
   `track(tracking_number) -> TrackingStatus`.
3. Add credentials as environment variables (secrets on the backend only).
4. Use webhooks or polling for tracking updates (same idempotent pattern as payments).
5. Write tests with mocked HTTP responses and update this document and ENVIRONMENT_VARIABLES.md.
