# Monitoring

## Signals to watch
| Signal | Source | Alert when |
|--------|--------|-----------|
| Site up | External uptime monitor (e.g. UptimeRobot, Better Stack) on `/api/v1/health` and `/` | 2 consecutive failures |
| Database reachable | `/api/v1/health?deep=1` (runs `SELECT 1`) | failure |
| 5xx rate | Backend JSON logs (`status >= 500`) | > 1% over 5 min |
| Payment issues | Admin dashboard "Needs attention": `payment_review` orders, failed refunds, webhook processing errors | any |
| Unprocessed webhooks | `payment_events.processed_at IS NULL AND received_at < now() - 10 min` | any |
| Email failures | `email_outbox.status = 'failed'` | any |
| Stale gold rate | Dashboard warning (rate older than `gold_rate_stale_after_hours`) | daily |
| Low stock | Dashboard low-stock list | daily review |
| Slow requests | Logs `duration_ms` p95 | > 1 s |

## Logs
* The backend writes one JSON line per request (`request_id`, `method`, `path`, `status`,
  `duration_ms`, `user_id`) plus application events (`event=order.paid`, `event=webhook.duplicate`).
* `request_id` is returned in the `X-Request-ID` header and in error bodies. Ask customers for it when
  they report a problem.
* Ship logs with the host's log driver (e.g. Docker `json-file` + a collector, or the platform's log
  view). Sensitive fields are redacted by `app/core/logging.py` (see SECURITY_MODEL §4).

## Health endpoints
* `GET /api/v1/health` → `{"status":"ok"}` (no DB, cheap).
* `GET /api/v1/health?deep=1` → also checks the database and reports the migration revision.

## Error tracking (optional)
Sentry or a similar tool can be added through the `SENTRY_DSN` environment variable (not yet
implemented — see KNOWN_LIMITATIONS). Personal data scrubbing must be enabled if it is added.
