"""Draft content pages loaded by the seed. All are flagged `is_draft_template=True`:
the owner must review them, and policy pages also need a qualified lawyer's review.
Text in [square brackets] is a placeholder for business facts we do not know.
"""

from __future__ import annotations

DRAFT_NOTE = (
    "> **Draft template.** This page was prepared as a starting point and must be reviewed and "
    "approved by the store owner{legal} before launch. Text in [square brackets] needs real "
    "business details.\n\n"
)


def _draft(legal: bool) -> str:
    return DRAFT_NOTE.format(legal=" and a qualified lawyer" if legal else "")


PAGES: list[dict[str, str | bool]] = [
    {
        "slug": "about",
        "title": "Our story",
        "summary": "Who we are and how we work.",
        "body": _draft(False)
        + """[Brand story — to be written by the owner: when and where the business started, the
people behind it, and what makes its jewellery distinctive.]

## How we price our jewellery
We show every price with an itemised breakdown — gold value at the current rate for its purity,
making charges, any stones, and GST — so you always know what you are paying for.

## Visit or contact us
[Showroom address and opening hours — to be configured.]
""",
        "legal": False,
    },
    {
        "slug": "faq",
        "title": "Frequently asked questions",
        "summary": "Answers about pricing, delivery, payments and returns.",
        "body": _draft(False)
        + """## Why do prices change?
Gold jewellery is priced from the gold rate for its purity, which changes over time. When a price
changes after you add an item to your cart, we show you the new price and ask you to accept it
before you pay. Once your order is placed, its price is fixed.

## What is included in the price?
Each product page lists the gold value, making charges, stone value (if any) and GST separately.

## Which payment methods do you accept?
Payments are processed securely by Razorpay. Available methods (such as UPI, cards and net
banking) are shown at checkout. We never see or store your card details.

## How long does delivery take?
Enter your PIN code on any product page to see the delivery options and estimated dates for your
area.

## Can I return or exchange an item?
Eligibility depends on the product and is shown on each product page. See our
[returns and exchanges policy](/returns-and-exchanges).

## Is the jewellery hallmarked?
Hallmark and HUID details are shown on a product page only when they have been verified for that
piece. [Owner to confirm hallmarking practice.]
""",
        "legal": False,
    },
    {
        "slug": "jewellery-care",
        "title": "Caring for your gold jewellery",
        "summary": "Simple habits that keep gold looking its best.",
        "body": _draft(False)
        + """## Everyday care
- Put jewellery on **after** perfume, hairspray and lotions, and take it off before swimming,
  exercising, cleaning or cooking.
- Chlorine and harsh household chemicals can damage gold alloys and stones.
- Wipe pieces with a soft, lint-free cloth after wearing to remove oils.

## Storage
- Store each piece separately in a soft pouch or a lined box so pieces don't scratch each other.
- Fasten chains before storing them to prevent tangles.

## Cleaning at home
- Soak plain gold briefly in lukewarm water with a few drops of mild soap, brush very gently with a
  soft toothbrush, rinse and dry with a soft cloth.
- Pieces with stones, pearls or enamel need gentler care — ask us before cleaning them.

## Professional check-ups
Have clasps, prongs and settings checked periodically, especially on pieces you wear every day.
[Owner to add any in-store cleaning or inspection services.]
""",
        "legal": False,
    },
    {
        "slug": "gold-buying-guide",
        "title": "Gold buying guide",
        "summary": "Purity, hallmarks and how gold jewellery is priced.",
        "body": _draft(False)
        + """## Purity (karat)
Karat describes how much of the metal is pure gold:

| Karat | Gold content | Typical use |
|-------|--------------|-------------|
| 24K | about 99.9% | Coins and bars; too soft for most jewellery |
| 22K | about 91.6% | Traditional Indian jewellery |
| 18K | 75% | Stone-set and contemporary jewellery |
| 14K | about 58.5% | Durable everyday pieces |

Lower karat gold contains more alloy metals, which makes it harder-wearing.

## Hallmarking
In India, gold jewellery is hallmarked under the Bureau of Indian Standards (BIS) scheme, and each
hallmarked piece carries a 6-digit HUID (Hallmark Unique Identification) code. Ask for these
details when you buy, and check them with BIS's official tools. We display hallmark information on
a product only when it has been verified for that piece.

## How a price is made up
- **Gold value** = net gold weight × the gold rate for that purity.
- **Making charges** — the cost of craftsmanship, shown as a per-gram rate, a percentage or a fixed
  amount depending on the piece.
- **Stones and other materials**, where present, are listed separately.
- **GST** is added and shown separately.

## Gross weight vs net weight
Gross weight is the weight of the whole piece. Net gold weight excludes stones and other
materials. Gold value is calculated on the net gold weight.
""",
        "legal": False,
    },
    {
        "slug": "shipping-policy",
        "title": "Shipping policy",
        "summary": "Delivery areas, timelines and charges.",
        "body": _draft(True)
        + """## Where we deliver
We deliver to serviceable PIN codes in India. Enter your PIN code on a product page or at checkout
to confirm availability.

## Delivery times and charges
Available delivery methods, charges and estimated delivery dates are shown at checkout before you
pay. [Owner to describe courier partners, packaging and insurance.]

## Dispatch
Orders are dispatched within [X] business days after payment is confirmed. You will receive an
email with tracking details when your order ships.

## Receiving your order
[Owner to describe signature/OTP requirements and what to do if a package looks tampered with.]
""",
        "legal": True,
    },
    {
        "slug": "returns-and-exchanges",
        "title": "Returns and exchanges",
        "summary": "How to return or exchange a piece.",
        "body": _draft(True)
        + """## Eligibility
Whether a piece can be returned or exchanged, and within how many days of delivery, is shown on its
product page. [Owner to list exclusions, e.g. customised or engraved pieces.]

## How to request a return or exchange
Sign in, open the order in **My account → Orders** and choose **Request return or exchange**.
Guests can contact us with their order reference.

## Condition of returned items
[Owner to specify the required condition, packaging, tags and documents.]

## Refunds
Approved refunds are made to the original payment method. See our [refund policy](/refund-policy).
""",
        "legal": True,
    },
    {
        "slug": "refund-policy",
        "title": "Refund policy",
        "summary": "When and how refunds are issued.",
        "body": _draft(True)
        + """## Cancelled orders
If you cancel a paid order before it is processed, a full refund is issued to the original payment
method.

## Returns
Refunds for approved returns are issued after the item is received and inspected.
[Owner to specify any deductions and the inspection timeline.]

## Timelines
Once we issue a refund, the time it takes to reach your account depends on your bank or payment
provider. [Owner to state typical timelines.]
""",
        "legal": True,
    },
    {
        "slug": "privacy-policy",
        "title": "Privacy policy",
        "summary": "How we collect, use and protect your personal data.",
        "body": _draft(True)
        + """## What we collect
- Account details: name, email address, phone number and password (stored only as a secure hash).
- Order details: delivery and billing addresses, items purchased, and payment status.
- Payment card and UPI details are handled by our payment provider, Razorpay, and are never stored
  by us.
- Technical data needed to keep the site secure (for example, IP address on sign-in).

## How we use it
To process orders, provide customer service, keep accounts secure and, if you opt in, send our
newsletter. [Owner/lawyer to confirm purposes and legal bases.]

## Sharing
We share data only with service providers needed to run the store (payments, delivery, email).
[List providers.]

## Your choices
You can update your details in your account, unsubscribe from emails at any time, and contact us
to ask about your data. [Lawyer to align with applicable Indian data-protection law.]

## Contact
[Grievance officer / contact details — to be configured.]
""",
        "legal": True,
    },
    {
        "slug": "terms-and-conditions",
        "title": "Terms and conditions",
        "summary": "The terms that apply when you use this site and place an order.",
        "body": _draft(True)
        + """## About us
This website is operated by [legal business name], [registered address], GSTIN [GSTIN].

## Prices
Prices are shown in Indian rupees and include GST. Gold-based prices depend on the current gold
rate; the price you pay is the price shown when you place your order.

## Orders
An order is confirmed only when payment has been verified. We may cancel and fully refund an order
if an item becomes unavailable. [Lawyer to complete.]

## Liability, governing law and disputes
[To be drafted by a qualified lawyer.]
""",
        "legal": True,
    },
]
