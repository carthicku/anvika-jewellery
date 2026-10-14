# Seed Data

`python -m app.cli seed` loads **deterministic, fictional** development data. It is idempotent: it
updates rows matched by natural keys (slug, SKU, code) instead of duplicating them, so running it
twice is safe. It refuses to run when `APP_ENV=production` unless `--allow-production` is passed
(and you should not do that).

## What gets created
| Data | Details |
|------|---------|
| Categories | Rings, Earrings, Necklaces, Pendants, Bangles, Bracelets, Chains, Mangalsutra |
| Collections | Everyday Gold, Bridal Heirlooms, Temple Classics, Minimal Diamonds (sample) |
| Products | ~32 fictional designs spanning 22K / 18K / 14K, weight-based and fixed pricing, some with sample stone values, some with size variants; all flagged `is_sample = true` |
| Images | Original line-art placeholder SVGs (no third-party photos), marked as placeholders |
| Stock | Mixed: plenty, low (≤ 2), one-of-a-kind (1), and out of stock (0) to exercise every UI state |
| Gold rates | **Illustrative** per-gram rates for 24K, 22K, 18K, 14K with the source note "Illustrative development rate — not market data" |
| Tax settings | Placeholder GST percentages (see ASSUMPTIONS P3) |
| Shipping | "Insured Standard Delivery" (free above a threshold) and "Express"; no zone restrictions |
| Content pages | Draft templates for about, FAQ, care guide, buying guide and policies, flagged as drafts that need owner/legal review |
| Coupons | `WELCOME5` (5% up to a cap, minimum order) and `EXPIRED10` (expired — for testing error messages) |
| Discount | "10% off making charges" on the Everyday Gold collection |

No user accounts are seeded. Create the admin with `python -m app.cli create-admin`. Create
customers by registering in the UI, or with `python -m app.cli create-customer` (development only,
for tests).

## Before launch
Run `python -m app.cli catalogue-report --samples` to list every `is_sample` record, then archive or
replace them in the admin. Replace the illustrative gold rates with real rates, and review every
draft content page. These steps are part of the [production checklist](../operations/PRODUCTION_CHECKLIST.md).
