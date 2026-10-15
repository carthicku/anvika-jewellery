"""Payment providers behind one small interface (ADR-0005, docs/architecture/PAYMENT_FLOW.md).

* `RazorpayGateway` talks to the Razorpay REST API with httpx (no SDK). Amounts are integer paise.
* `SimulatorGateway` is for development and automated tests only: no network, no money. Its payment
  ids are signed with SIMULATOR_SECRET, so "fetching" a payment is verifiable without storing
  anything, and it produces Razorpay-style checkout signatures so the real verification code runs.
  Settings validation refuses PAYMENT_PROVIDER=simulator in production.

Card numbers, CVV, UPI PINs and bank credentials never reach this server (Razorpay's pop-up
collects them), so nothing here can store them.
"""

from __future__ import annotations

import contextlib
import hashlib
import hmac
import logging
import secrets
import threading
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.core.config import Settings
from app.core.errors import PaymentProviderError

logger = logging.getLogger("app.payments")

# Fields kept from provider payloads; everything else (card/bank/VPA details, contact info) is
# dropped before anything is stored or logged.
SAFE_PAYMENT_FIELDS = (
    "id",
    "entity",
    "order_id",
    "amount",
    "currency",
    "status",
    "method",
    "captured",
    "error_code",
    "error_description",
    "error_reason",
    "refund_status",
    "amount_refunded",
    "created_at",
    "payment_id",
)


def sanitise(entity: dict[str, Any] | None) -> dict[str, Any]:
    return {k: entity[k] for k in SAFE_PAYMENT_FIELDS if entity and k in entity}


def hmac_sha256(secret: str, message: str | bytes) -> str:
    data = message.encode() if isinstance(message, str) else message
    return hmac.new(secret.encode(), data, hashlib.sha256).hexdigest()


@dataclass(frozen=True)
class ProviderOrder:
    id: str
    amount_paise: int
    currency: str


@dataclass(frozen=True)
class ProviderPayment:
    id: str
    order_id: str | None
    status: str  # created | authorized | captured | refunded | failed
    amount_paise: int
    currency: str
    method: str | None = None
    error_code: str | None = None
    error_description: str | None = None

    @classmethod
    def from_entity(cls, entity: dict[str, Any]) -> ProviderPayment:
        return cls(
            id=str(entity["id"]),
            order_id=entity.get("order_id"),
            status=str(entity.get("status", "")),
            amount_paise=int(entity.get("amount", 0)),
            currency=str(entity.get("currency", "")),
            method=entity.get("method"),
            error_code=entity.get("error_code"),
            error_description=entity.get("error_description"),
        )


@dataclass(frozen=True)
class ProviderRefund:
    id: str
    status: str  # pending | processed | failed
    amount_paise: int


class PaymentGateway(Protocol):
    name: str
    key_id: str

    def create_order(self, amount_paise: int, receipt: str, notes: dict[str, str]) -> ProviderOrder:
        """Create a provider order for exactly this amount."""

    def fetch_payment(self, payment_id: str) -> ProviderPayment:
        """Fetch one payment from the provider (the source of truth)."""

    def payments_for_order(self, provider_order_id: str) -> list[ProviderPayment]:
        """All payments made against a provider order (for reconciliation)."""

    def refund(self, payment_id: str, amount_paise: int, notes: dict[str, str]) -> ProviderRefund:
        """Refund (part of) a captured payment."""

    def verify_checkout_signature(
        self, provider_order_id: str, payment_id: str, signature: str
    ) -> bool:
        """Check the signature returned to the browser by the checkout pop-up."""


# --------------------------------------------------------------------------------------------
# Razorpay
# --------------------------------------------------------------------------------------------


class RazorpayGateway:
    name = "razorpay"

    def __init__(
        self,
        key_id: str,
        key_secret: str,
        api_base: str = "https://api.razorpay.com/v1",
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.key_id = key_id
        self._secret = key_secret
        self._client = httpx.Client(
            base_url=api_base.rstrip("/"),
            auth=(key_id, key_secret),
            timeout=httpx.Timeout(10.0, connect=5.0),
            transport=transport,
        )

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = self._client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            logger.warning("Razorpay %s %s failed: %s", method, path, type(exc).__name__)
            raise PaymentProviderError(
                "We couldn't reach the payment provider. Please try again in a moment."
            ) from exc
        if response.status_code >= 400:
            # Razorpay error bodies contain no secrets; keep only the code/description.
            error = {}
            with contextlib.suppress(ValueError):
                error = response.json().get("error", {})
            logger.warning(
                "Razorpay %s %s -> %s %s", method, path, response.status_code, error.get("code")
            )
            raise PaymentProviderError(
                "The payment provider rejected the request. Please try again.",
                details={"provider_code": error.get("code")},
            )
        data: dict[str, Any] = response.json()
        return data

    def create_order(self, amount_paise: int, receipt: str, notes: dict[str, str]) -> ProviderOrder:
        data = self._request(
            "POST",
            "/orders",
            json={"amount": amount_paise, "currency": "INR", "receipt": receipt, "notes": notes},
        )
        return ProviderOrder(str(data["id"]), int(data["amount"]), str(data["currency"]))

    def fetch_payment(self, payment_id: str) -> ProviderPayment:
        return ProviderPayment.from_entity(self._request("GET", f"/payments/{payment_id}"))

    def payments_for_order(self, provider_order_id: str) -> list[ProviderPayment]:
        data = self._request("GET", f"/orders/{provider_order_id}/payments")
        return [ProviderPayment.from_entity(item) for item in data.get("items", [])]

    def refund(self, payment_id: str, amount_paise: int, notes: dict[str, str]) -> ProviderRefund:
        data = self._request(
            "POST", f"/payments/{payment_id}/refund", json={"amount": amount_paise, "notes": notes}
        )
        return ProviderRefund(str(data["id"]), str(data.get("status", "pending")), amount_paise)

    def verify_checkout_signature(
        self, provider_order_id: str, payment_id: str, signature: str
    ) -> bool:
        expected = hmac_sha256(self._secret, f"{provider_order_id}|{payment_id}")
        return hmac.compare_digest(expected, signature)


def verify_webhook_signature(secret: str, raw_body: bytes, signature: str | None) -> bool:
    """Razorpay signs the exact raw request body with the webhook secret."""
    if not secret or not signature:
        return False
    return hmac.compare_digest(hmac_sha256(secret, raw_body), signature)


# --------------------------------------------------------------------------------------------
# Simulator (development / tests only)
# --------------------------------------------------------------------------------------------

SIMULATOR_OUTCOMES = ("captured", "authorized", "failed")
_OUTCOME_CODES = {outcome[0]: outcome for outcome in SIMULATOR_OUTCOMES}


class SimulatorGateway:
    """Behaves like Razorpay's API for the parts we use. No network calls, no money."""

    name = "simulator"
    key_id = "sim_test_key"

    def __init__(self, secret: str) -> None:
        self._secret = secret
        self._lock = threading.Lock()
        self._orders: dict[str, int] = {}
        self._payments: dict[str, list[str]] = {}
        self._refunded: set[str] = set()
        # Lets tests simulate provider outages.
        self.fail_requests = False

    def _check_up(self) -> None:
        if self.fail_requests:
            raise PaymentProviderError(
                "We couldn't reach the payment provider. Please try again in a moment."
            )

    def create_order(self, amount_paise: int, receipt: str, notes: dict[str, str]) -> ProviderOrder:
        self._check_up()
        order_id = "order_sim_" + secrets.token_hex(7)
        with self._lock:
            self._orders[order_id] = amount_paise
        return ProviderOrder(order_id, amount_paise, "INR")

    def simulate_payment(
        self, provider_order_id: str, amount_paise: int, outcome: str
    ) -> tuple[ProviderPayment, str]:
        """What the checkout pop-up would do: returns the payment and its checkout signature."""
        if outcome not in SIMULATOR_OUTCOMES:
            raise ValueError(f"Unknown simulator outcome {outcome!r}")
        # Compact, signed id: pay_sim_<order hex>_<paise>_<c|a|f>_<nonce>_<tag> (< 80 chars).
        order_hex = provider_order_id.removeprefix("order_sim_")
        body = f"{order_hex}_{amount_paise}_{outcome[0]}_{secrets.token_hex(4)}"
        payment_id = f"pay_sim_{body}_{hmac_sha256(self._secret, body)[:24]}"
        with self._lock:
            self._payments.setdefault(provider_order_id, []).append(payment_id)
        signature = hmac_sha256(self._secret, f"{provider_order_id}|{payment_id}")
        return self.fetch_payment(payment_id), signature

    def fetch_payment(self, payment_id: str) -> ProviderPayment:
        self._check_up()
        data: dict[str, str] | None = None
        body, _, tag = payment_id.removeprefix("pay_sim_").rpartition("_")
        parts = body.split("_")
        if (
            payment_id.startswith("pay_sim_")
            and len(parts) == 4
            and hmac.compare_digest(hmac_sha256(self._secret, body)[:24], tag)
        ):
            data = {"o": f"order_sim_{parts[0]}", "a": parts[1], "s": _OUTCOME_CODES[parts[2]]}
        if data is None:
            raise PaymentProviderError(
                "The payment provider rejected the request. Please try again.",
                details={"provider_code": "BAD_REQUEST_ERROR"},
            )
        status = "refunded" if payment_id in self._refunded else str(data["s"])
        return ProviderPayment(
            id=payment_id,
            order_id=str(data["o"]),
            status=status,
            amount_paise=int(data["a"]),
            currency="INR",
            method="upi" if status != "failed" else None,
            error_code="BAD_REQUEST_ERROR" if status == "failed" else None,
            error_description="Simulated failure: the payment was declined."
            if status == "failed"
            else None,
        )

    def payments_for_order(self, provider_order_id: str) -> list[ProviderPayment]:
        self._check_up()
        with self._lock:
            ids = list(self._payments.get(provider_order_id, []))
        return [self.fetch_payment(pid) for pid in ids]

    def capture_later(self, payment_id: str) -> str:
        """Test helper: the provider captures an authorised payment (returns the new id)."""
        payment = self.fetch_payment(payment_id)
        if payment.order_id is None:
            raise ValueError("Simulated payment without an order")
        captured, _ = self.simulate_payment(payment.order_id, payment.amount_paise, "captured")
        with self._lock:
            self._payments[payment.order_id].remove(payment_id)
        return captured.id

    def refund(self, payment_id: str, amount_paise: int, notes: dict[str, str]) -> ProviderRefund:
        self._check_up()
        self.fetch_payment(payment_id)
        with self._lock:
            self._refunded.add(payment_id)
        return ProviderRefund("rfnd_sim_" + secrets.token_hex(7), "processed", amount_paise)

    def verify_checkout_signature(
        self, provider_order_id: str, payment_id: str, signature: str
    ) -> bool:
        expected = hmac_sha256(self._secret, f"{provider_order_id}|{payment_id}")
        return hmac.compare_digest(expected, signature)


def make_gateway(settings: Settings) -> PaymentGateway:
    if settings.payment_provider == "razorpay":
        return RazorpayGateway(
            settings.razorpay_key_id,
            settings.razorpay_key_secret.get_secret_value(),
            settings.razorpay_api_base,
        )
    if settings.is_production:  # settings validation already refuses this; belt and braces
        raise RuntimeError("The payment simulator cannot run in production")
    return SimulatorGateway(settings.simulator_secret.get_secret_value())
