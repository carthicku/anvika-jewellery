# Incident Response

Keep calm, protect customers' money and data first, then restore service, then learn.

## Severity
| Level | Examples | Response |
|-------|----------|----------|
| SEV1 | Site down; customers charged but orders not created; data breach suspected; secrets leaked | Immediately, all hands |
| SEV2 | Checkout failing for some payment methods; emails not sending; admin unusable | Within 2 hours |
| SEV3 | Cosmetic bugs, slow pages | Next working day |

## Playbooks
### Customers report "money debited, no order confirmation"
1. Find the payment in the Razorpay dashboard (payment id from the customer).
2. In Admin → Orders, search by email/phone; open the order and check its payment attempts and
   events.
3. Run `python -m app.cli reconcile-payments --since <time>`. It fetches payment states from Razorpay
   and applies the same idempotent logic as webhooks.
4. If the order is in `payment_review`, decide: fulfil (if stock exists) or refund. Inform the
   customer.

### Webhooks failing
Check the Razorpay dashboard → Webhooks → delivery logs (status codes). A 400 means the secret is
wrong or the body was modified. Fix it; Razorpay retries deliveries for a period, and reconciliation
covers the gap.

### Suspected secret leak (e.g. `.env` pushed to Git)
1. **Rotate immediately**: Razorpay key secret and webhook secret (dashboard), SMTP password,
   storage keys, database password (Supabase), `SECRET_KEY` (signs everyone out).
2. Remove the secret from Git history (`git filter-repo`) and force-push only after rotating. Rotation
   matters more than history cleanup.
3. Review Razorpay and Supabase logs for misuse.

### Suspected account compromise (admin)
Deactivate the user (Admin → Users, or `python -m app.cli deactivate-user --email …`). This revokes
all their sessions immediately. Then review `audit_logs` for their actions and rotate any secrets
they could see.

### Database problem
See BACKUP_AND_RESTORE.md. Put the site in maintenance mode before restoring.

## Communication
* Personal data breach: Indian law (Digital Personal Data Protection Act, 2023 and its rules) has
  notification obligations. **Consult a lawyer immediately**; this document does not give legal
  advice.
* Customer messages: be honest and specific about what happened and what you are doing.

## After the incident
Write a short blameless review (what happened, timeline, impact, root cause, fixes) in
`docs/operations/incidents/YYYY-MM-DD-title.md`, and add follow-up tasks.
