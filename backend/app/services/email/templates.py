"""Email templates: plain text + simple, brand-consistent HTML (escaped). Kept in code so they are
reviewed with the business logic that sends them. See docs/operations/EMAIL_SETUP.md."""

from __future__ import annotations

from html import escape
from typing import Any

# (heading, paragraphs, (button label, url-key) | None, footnote)
TemplateSpec = tuple[str, list[str], tuple[str, str] | None, str]

TEMPLATES: dict[str, TemplateSpec] = {
    "verify_email": (
        "Confirm your email address",
        ["Hello {name},", "Please confirm the email address for your {store_name} account."],
        ("Confirm email", "verify_url"),
        "This link expires in 48 hours. If you didn't create an account, you can ignore this "
        "email.",
    ),
    "password_reset": (
        "Reset your password",
        ["Hello {name},", "We received a request to reset the password for your account."],
        ("Choose a new password", "reset_url"),
        "This link expires in 30 minutes and can be used once. If you didn't ask for this, you can "
        "ignore this email — your password won't change.",
    ),
    "password_changed": (
        "Your password was changed",
        [
            "Hello {name},",
            "The password for your {store_name} account was just changed and other devices were "
            "signed out.",
        ],
        None,
        "If this wasn't you, reset your password immediately and contact us.",
    ),
    "order_confirmation": (
        "Thank you — your order is confirmed",
        [
            "Hello {name},",
            "We've received your payment for order {reference}. Total paid: {total}.",
            "Items: {items}",
            "We'll email you again when your order ships.",
        ],
        ("View your order", "order_url"),
        "Please keep this email for your records. Your tax invoice will be shared with your "
        "shipment.",
    ),
    "order_cancelled": (
        "Your order has been cancelled",
        [
            "Hello {name},",
            "Order {reference} ({total}) has been cancelled.",
            "Items: {items}",
            "If you had already paid, a full refund has been requested. We'll email you when it "
            "is processed; how long it then takes to reach you depends on your bank.",
        ],
        ("View your order", "order_url"),
        "If you didn't ask for this cancellation, please contact us.",
    ),
    "order_shipped": (
        "Your order is on its way",
        [
            "Hello {name},",
            "Good news — order {reference} has been shipped.",
            "Items: {items}",
            "You can follow the delivery with the tracking details on your order page.",
        ],
        ("Track your order", "order_url"),
        "Please check the package seal when it arrives and contact us if anything looks wrong.",
    ),
    "return_update": (
        "Update on your return or exchange",
        [
            "Hello {name},",
            "{return_kind} for order {reference}: {return_message}",
        ],
        ("View your order", "order_url"),
        "If you have questions, reply to this email or contact us.",
    ),
    "refund_processed": (
        "Your refund has been processed",
        [
            "Hello {name},",
            "We've processed a refund of {refund_amount} for order {reference}.",
            "How long it takes to reach your account depends on your bank and payment method.",
        ],
        ("View your order", "order_url"),
        "If you have questions about this refund, reply to this email or contact us.",
    ),
}


def render(template: str, context: dict[str, Any]) -> tuple[str, str]:
    """Return (text, html) for a template. Unknown templates raise KeyError (a programming bug)."""
    heading, paragraphs, button, footnote = TEMPLATES[template]
    values = {k: ("" if v is None else str(v)) for k, v in context.items()}
    text_paragraphs = [p.format(**values) for p in paragraphs]
    button_url = values.get(button[1], "") if button else ""

    text = "\n\n".join([heading, *text_paragraphs])
    if button:
        text += f"\n\n{button[0]}: {button_url}"
    text += f"\n\n{footnote}\n\n— {values.get('store_name', '')}\n"

    html_paragraphs = "".join(
        f'<p style="margin:0 0 16px;line-height:1.6">{escape(p.format(**values))}</p>'
        for p in paragraphs
    )
    html_button = (
        f'<p style="margin:24px 0"><a href="{escape(button_url, quote=True)}" '
        'style="background:#1F1D1A;color:#FAF7F2;padding:12px 24px;border-radius:2px;'
        f'text-decoration:none;display:inline-block">{escape(button[0])}</a></p>'
        if button
        else ""
    )
    store = escape(values.get("store_name", ""))
    html = (
        '<!doctype html><html><body style="margin:0;background:#FAF7F2;'
        'font-family:Arial,sans-serif;color:#1F1D1A">'
        '<div style="max-width:560px;margin:0 auto;padding:40px 24px">'
        f'<p style="font-family:Georgia,serif;letter-spacing:6px;font-size:20px;margin:0 0 32px">'
        f"{store.upper()}</p>"
        f'<h1 style="font-family:Georgia,serif;font-weight:normal;font-size:26px;margin:0 0 20px">'
        f"{escape(heading)}</h1>{html_paragraphs}{html_button}"
        f'<p style="font-size:13px;color:#5C574F;line-height:1.6">{escape(footnote)}</p>'
        f'<hr style="border:none;border-top:1px solid #E6DFD3;margin:32px 0">'
        f'<p style="font-size:12px;color:#6F695F">{store}</p></div></body></html>'
    )
    return text, html
