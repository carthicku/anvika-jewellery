# Email Setup

Design: [ADR-0008](../architecture/ADR/0008-email-outbox.md). Templates:
`backend/app/services/email/templates/`.

## Development
`EMAIL_BACKEND=file` (default) writes every email as an `.eml` file to `backend/var/mail/`. Open one
with any mail client or a text editor. The outbox row is marked `written_to_sink`, never `sent`.

## Production (SMTP)
1. Choose a transactional email provider with an Indian or Asia-Pacific presence and good
   deliverability (e.g. Amazon SES Mumbai, Postmark, Zoho ZeptoMail, Brevo). Compare current pricing.
2. Verify your sending domain with the provider. Add the DNS records it gives you:
   * **SPF** (`TXT v=spf1 include:<provider> ~all`)
   * **DKIM** (CNAME/TXT records from the provider)
   * **DMARC** (`TXT _dmarc  v=DMARC1; p=none; rua=mailto:dmarc@<domain>`, tightened later)
3. Set:
   ```
   EMAIL_BACKEND=smtp
   EMAIL_FROM="<Brand> <orders@your-domain>"
   SMTP_HOST=...
   SMTP_PORT=587
   SMTP_USERNAME=...
   SMTP_PASSWORD=...      # secret
   SMTP_STARTTLS=true
   ```
4. Send a test: `python -m app.cli send-test-email --to you@example.com`.
5. Check that it arrives in Gmail and Outlook inboxes (not spam) and that links point to
   `PUBLIC_SITE_URL`.

## Templates and triggers
| Template | Trigger | Idempotency key |
|----------|---------|-----------------|
| `verify_email` | Registration / resend | `verify_email:<token_id>` |
| `password_reset` | Forgot password | `password_reset:<token_id>` |
| `order_confirmation` | Order paid | `order_confirmation:<order_id>` |
| `payment_confirmation` | Folded into order confirmation (one email) | — |
| `order_status` | processing / delivered | `order_status:<order_id>:<status>` |
| `shipment_dispatched` | Shipment added | `shipment:<shipment_id>` |
| `order_cancelled` | Cancellation | `order_cancelled:<order_id>` |
| `refund_update` | Refund processed/failed | `refund:<refund_id>:<status>` |
| `return_update` | Return status change | `return:<return_id>:<status>` |
| `contact_ack` | Contact form (optional) | `contact:<enquiry_id>` |

Failures retry up to 5 times with back-off, then stay `failed` and appear in the admin.
