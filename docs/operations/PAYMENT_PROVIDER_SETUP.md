# Payment Provider Setup (Razorpay)

Flow and security rules: [PAYMENT_FLOW.md](../architecture/PAYMENT_FLOW.md).

## 1. Test mode (do this first)
1. Create a Razorpay account and switch the dashboard to **Test Mode**.
2. *Account & Settings → API Keys → Generate Test Key*. You get a **Key Id** (`rzp_test_…`) and a
   **Key Secret** (shown once — store it in your password manager).
3. In `backend/.env`:
   ```
   PAYMENT_PROVIDER=razorpay
   RAZORPAY_KEY_ID=<your rzp_test_... key id>
   RAZORPAY_KEY_SECRET=<your test key secret>
   RAZORPAY_WEBHOOK_SECRET=<a long random string you choose>
   ```
4. **Webhooks** (*Account & Settings → Webhooks → Add New Webhook*):
   * URL: `https://<your-domain>/api/v1/webhooks/razorpay`. Razorpay cannot reach `localhost`. For
     local testing, use a tunnelling tool such as `cloudflared tunnel` or `ngrok`, or rely on the
     verify endpoint plus `python -m app.cli reconcile-payments`.
   * Secret: the same value as `RAZORPAY_WEBHOOK_SECRET`.
   * Events: `payment.authorized`, `payment.captured`, `payment.failed`, `order.paid`,
     `refund.processed`, `refund.failed`.
5. Payment capture: in *Account & Settings → Payment capture*, choose **automatic capture**. Our
   backend treats only `captured` payments as paid.
6. Test with Razorpay's test cards/UPI ids from their documentation ("Test card details" page).
   Test both a successful and a failed payment.

## 2. What the code does with these values
| Value | Used by | Exposed to browser? |
|-------|---------|---------------------|
| Key Id | Sent in the `/checkout/orders` response for Checkout.js | Yes (it is public by design) |
| Key Secret | Basic auth for the Orders/Payments/Refunds APIs; checkout signature HMAC | **Never** |
| Webhook Secret | Webhook HMAC verification | **Never** |

## 3. Going live
1. Complete Razorpay KYC/activation for the business.
2. Generate **live** keys and create a separate live webhook with a **different** secret.
3. Put the live values only in the production secret store. Keep test keys in staging.
4. Make one small real purchase and refund it.
5. Re-check the Razorpay domains needed in the Content-Security-Policy.

## 4. Reconciliation
`python -m app.cli reconcile-payments --since 2026-10-14T00:00:00Z` fetches the payments for every
attempt created since that time and applies any missed captures/failures idempotently. Run it after
any webhook outage.

## 5. Payment simulator (development only)
`PAYMENT_PROVIDER=simulator` needs no keys and shows a clearly labelled simulated payment dialog. It
cannot be enabled in production. See ADR-0005.
