"""Fictional, deterministic sample catalogue for development (docs/development/SEED_DATA.md).

Everything here is SAMPLE data: product names, weights, stone values and rates are invented for
development and testing. No hallmark/HUID/certification claims are made for any sample product.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal as D

CATEGORIES = [
    # slug, name, description, illustration
    ("rings", "Rings", "Solitaires, bands and everyday rings.", "ring-solitaire"),
    ("earrings", "Earrings", "Studs, drops and jhumkas.", "earrings-jhumka"),
    ("necklaces", "Necklaces", "From delicate layers to statement pieces.", "necklace"),
    ("pendants", "Pendants", "Pendants to wear alone or layered.", "pendant"),
    ("bangles", "Bangles", "Classic and contemporary bangles.", "bangle"),
    ("bracelets", "Bracelets", "Link, chain and charm bracelets.", "bracelet"),
    ("chains", "Chains", "Fine and bold chains in solid gold.", "chain"),
    ("mangalsutra", "Mangalsutra", "Traditional and modern mangalsutras.", "mangalsutra"),
]

COLLECTIONS = [
    # slug, name, description, featured, illustration
    ("everyday-gold", "Everyday Gold", "Light pieces made for daily wear.", True, "chain"),
    (
        "bridal-heirlooms",
        "Bridal Heirlooms",
        "Statement pieces for the wedding season.",
        True,
        "necklace",
    ),
    (
        "temple-classics",
        "Temple Classics",
        "Motifs inspired by South Indian temple jewellery.",
        True,
        "earrings-jhumka",
    ),
    (
        "minimal-diamonds",
        "Minimal Diamonds",
        "Understated gold set with small stones.",
        False,
        "ring-solitaire",
    ),
]

# Illustrative development rates — NOT market data (SEED_DATA.md).
GOLD_RATES = {"24K": D("7800.00"), "22K": D("7150.00"), "18K": D("5850.00"), "14K": D("4550.00")}
RATE_SOURCE_NOTE = "Illustrative development rate — not market data"

SHIPPING_METHODS = [
    # code, name, description, fee, free_above, min_days, max_days, sort
    (
        "standard",
        "Standard delivery",
        "Tracked delivery to your door.",
        D("199.00"),
        D("25000.00"),
        4,
        7,
        0,
    ),
    (
        "express",
        "Express delivery",
        "Priority dispatch and faster delivery.",
        D("499.00"),
        None,
        2,
        3,
        1,
    ),
]


@dataclass
class VariantSpec:
    sku: str
    label: str = "Standard"
    size: str | None = None
    gross: D | None = None
    net: D | None = None
    stone_ct: D | None = None
    stone_value: D = D("0")
    other: D = D("0")
    other_label: str | None = None
    fixed: D | None = None
    stock: int = 5
    default: bool = False


@dataclass
class ProductSpec:
    slug: str
    name: str
    category: str
    purity: str
    illustration: str
    variants: list[VariantSpec]
    description: str
    model: str = "weight_based"
    colour: str = "yellow"
    making: tuple[str, D] = ("percent", D("12"))
    wastage: D | None = None
    collections: list[str] = field(default_factory=list)
    attrs: dict[str, str] = field(default_factory=dict)
    featured: bool = False
    bestseller: bool = False
    stone_details: str | None = None
    care: str = (
        "Store separately in a soft pouch. Avoid perfume, chlorine and harsh chemicals. "
        "Wipe gently with a soft, dry cloth after wearing."
    )
    returns: tuple[bool, bool, int | None] = (True, True, 15)
    published_days_ago: int = 60


def ring_sizes(
    prefix: str,
    base_gross: str,
    base_net: str,
    stock: list[int],
    stone_ct: str | None = None,
    stone_value: str = "0",
) -> list[VariantSpec]:
    """Ring sizes 10/12/14/16 with weight growing slightly per size."""
    out = []
    for i, size in enumerate(("10", "12", "14", "16")):
        bump = D("0.080") * i
        out.append(
            VariantSpec(
                sku=f"{prefix}-{size}",
                label=f"Size {size}",
                size=size,
                gross=D(base_gross) + bump,
                net=D(base_net) + bump,
                stone_ct=D(stone_ct) if stone_ct else None,
                stone_value=D(stone_value),
                stock=stock[i],
                default=(size == "12"),
            )
        )
    return out


SAMPLE_STONE_NOTE = "Sample data for development — stone details are illustrative, not verified."

PRODUCTS: list[ProductSpec] = [
    # ---------------------------------------------------------------- Rings
    ProductSpec(
        "aria-solitaire-ring",
        "Aria Solitaire Ring",
        "rings",
        "18K",
        "ring-solitaire",
        ring_sizes("ANV-RG-001", "2.900", "2.700", [3, 5, 2, 0], "0.25", "18500.00"),
        "A single stone held high in a slim four-prong setting.",
        colour="white",
        making=("percent", D("16")),
        collections=["minimal-diamonds"],
        attrs={"occasion": "engagement", "style": "minimal"},
        featured=True,
        stone_details=SAMPLE_STONE_NOTE,
        published_days_ago=10,
    ),
    ProductSpec(
        "everyday-gold-band",
        "Everyday Gold Band",
        "rings",
        "22K",
        "ring-band",
        ring_sizes("ANV-RG-002", "3.400", "3.400", [6, 8, 6, 4]),
        "A smooth comfort-fit band with a soft polished finish.",
        making=("per_gram", D("550")),
        collections=["everyday-gold"],
        attrs={"occasion": "everyday", "style": "minimal"},
        bestseller=True,
        published_days_ago=120,
    ),
    ProductSpec(
        "lotus-cocktail-ring",
        "Lotus Cocktail Ring",
        "rings",
        "22K",
        "ring-solitaire",
        ring_sizes("ANV-RG-003", "6.200", "6.000", [1, 1, 0, 0]),
        "Layered lotus petals in high-polish and matte gold.",
        making=("percent", D("14")),
        wastage=D("2"),
        collections=["temple-classics"],
        attrs={"occasion": "festive", "style": "traditional"},
        published_days_ago=30,
    ),
    ProductSpec(
        "rose-twist-ring",
        "Rose Twist Ring",
        "rings",
        "14K",
        "ring-band",
        ring_sizes("ANV-RG-004", "2.100", "2.100", [4, 4, 3, 2]),
        "Two strands of rose gold twisted into one fine band.",
        colour="rose",
        making=("flat", D("1800")),
        collections=["everyday-gold"],
        attrs={"occasion": "everyday", "style": "contemporary"},
        published_days_ago=5,
    ),
    # ---------------------------------------------------------------- Earrings
    ProductSpec(
        "meenakshi-jhumkas",
        "Meenakshi Jhumkas",
        "earrings",
        "22K",
        "earrings-jhumka",
        [VariantSpec("ANV-ER-001", gross=D("12.400"), net=D("12.100"), stock=2, default=True)],
        "Bell-shaped jhumkas with fine bead drops and temple motifs.",
        making=("percent", D("15")),
        wastage=D("3"),
        collections=["temple-classics", "bridal-heirlooms"],
        attrs={"occasion": "wedding", "style": "traditional"},
        featured=True,
        bestseller=True,
        published_days_ago=90,
    ),
    ProductSpec(
        "dewdrop-studs",
        "Dewdrop Studs",
        "earrings",
        "18K",
        "earrings-stud",
        [
            VariantSpec(
                "ANV-ER-002",
                gross=D("1.800"),
                net=D("1.700"),
                stone_ct=D("0.10"),
                stone_value=D("7200.00"),
                stock=7,
                default=True,
            )
        ],
        "Small round studs for everyday sparkle.",
        colour="white",
        making=("flat", D("2400")),
        collections=["minimal-diamonds", "everyday-gold"],
        attrs={"occasion": "everyday", "style": "minimal"},
        bestseller=True,
        stone_details=SAMPLE_STONE_NOTE,
        published_days_ago=200,
    ),
    ProductSpec(
        "crescent-hoops",
        "Crescent Hoops",
        "earrings",
        "22K",
        "earrings-stud",
        [VariantSpec("ANV-ER-003", gross=D("4.600"), net=D("4.600"), stock=5, default=True)],
        "Tapered hoops that sit close to the ear.",
        making=("per_gram", D("600")),
        collections=["everyday-gold"],
        attrs={"occasion": "office", "style": "contemporary"},
        published_days_ago=14,
    ),
    ProductSpec(
        "peacock-drops",
        "Peacock Drops",
        "earrings",
        "22K",
        "earrings-jhumka",
        [VariantSpec("ANV-ER-004", gross=D("8.300"), net=D("8.100"), stock=0, default=True)],
        "Drop earrings with a peacock motif and articulated tassels.",
        making=("percent", D("15")),
        collections=["temple-classics"],
        attrs={"occasion": "festive", "style": "traditional"},
        published_days_ago=60,
    ),
    # ---------------------------------------------------------------- Necklaces
    ProductSpec(
        "heritage-bridal-necklace",
        "Heritage Bridal Necklace",
        "necklaces",
        "22K",
        "necklace",
        [VariantSpec("ANV-NK-001", gross=D("48.500"), net=D("47.200"), stock=1, default=True)],
        "A one-of-a-kind collar necklace with graduated motifs.",
        making=("percent", D("18")),
        wastage=D("4"),
        collections=["bridal-heirlooms"],
        attrs={"occasion": "wedding", "style": "traditional"},
        featured=True,
        published_days_ago=20,
    ),
    ProductSpec(
        "layered-satellite-necklace",
        "Layered Satellite Necklace",
        "necklaces",
        "18K",
        "necklace",
        [
            VariantSpec(
                "ANV-NK-002",
                label="16 inch",
                size="16in",
                gross=D("6.200"),
                net=D("6.200"),
                stock=4,
                default=True,
            ),
            VariantSpec(
                "ANV-NK-003",
                label="18 inch",
                size="18in",
                gross=D("6.900"),
                net=D("6.900"),
                stock=3,
            ),
        ],
        "Two fine chains with small satellite beads, worn layered.",
        making=("percent", D("12")),
        collections=["everyday-gold"],
        attrs={"occasion": "everyday", "style": "contemporary"},
        published_days_ago=8,
    ),
    ProductSpec(
        "temple-lakshmi-haar",
        "Temple Lakshmi Haar",
        "necklaces",
        "22K",
        "necklace",
        [VariantSpec("ANV-NK-004", gross=D("62.000"), net=D("60.500"), stock=1, default=True)],
        "A long haar with coin motifs in the temple tradition.",
        making=("percent", D("16")),
        wastage=D("3"),
        collections=["temple-classics", "bridal-heirlooms"],
        attrs={"occasion": "wedding", "style": "traditional"},
        bestseller=True,
        published_days_ago=150,
    ),
    ProductSpec(
        "pearl-drop-necklace",
        "Pearl Drop Necklace",
        "necklaces",
        "18K",
        "necklace",
        [VariantSpec("ANV-NK-005", fixed=D("38500.00"), gross=D("5.100"), stock=2, default=True)],
        "Fine chain with a single drop; priced as a finished piece.",
        model="fixed",
        making=("none", D("0")),
        collections=["minimal-diamonds"],
        attrs={"occasion": "office", "style": "minimal"},
        stone_details=SAMPLE_STONE_NOTE,
        published_days_ago=40,
    ),
    # ---------------------------------------------------------------- Pendants
    ProductSpec(
        "om-pendant",
        "Om Pendant",
        "pendants",
        "22K",
        "pendant",
        [VariantSpec("ANV-PD-001", gross=D("2.300"), net=D("2.300"), stock=9, default=True)],
        "A hand-finished Om symbol pendant. Chain sold separately.",
        making=("per_gram", D("700")),
        collections=["everyday-gold"],
        attrs={"occasion": "everyday", "style": "traditional"},
        bestseller=True,
        published_days_ago=300,
    ),
    ProductSpec(
        "teardrop-pendant",
        "Teardrop Pendant",
        "pendants",
        "18K",
        "pendant",
        [
            VariantSpec(
                "ANV-PD-002",
                gross=D("1.900"),
                net=D("1.800"),
                stone_ct=D("0.15"),
                stone_value=D("9800.00"),
                stock=3,
                default=True,
            )
        ],
        "A teardrop outline framing a small stone.",
        colour="white",
        making=("flat", D("2600")),
        collections=["minimal-diamonds"],
        attrs={"occasion": "office", "style": "minimal"},
        featured=True,
        stone_details=SAMPLE_STONE_NOTE,
        published_days_ago=12,
    ),
    ProductSpec(
        "initial-disc-pendant",
        "Initial Disc Pendant",
        "pendants",
        "14K",
        "pendant",
        [VariantSpec("ANV-PD-003", fixed=D("12900.00"), gross=D("1.600"), stock=6, default=True)],
        "A polished disc pendant, priced as a finished piece.",
        model="fixed",
        making=("none", D("0")),
        colour="rose",
        collections=["everyday-gold"],
        attrs={"occasion": "everyday", "style": "contemporary"},
        published_days_ago=3,
    ),
    ProductSpec(
        "ganesha-pendant",
        "Ganesha Pendant",
        "pendants",
        "22K",
        "pendant",
        [VariantSpec("ANV-PD-004", gross=D("3.100"), net=D("3.100"), stock=0, default=True)],
        "A traditional Ganesha pendant with fine detailing.",
        making=("per_gram", D("750")),
        collections=["temple-classics"],
        attrs={"occasion": "festive", "style": "traditional"},
        published_days_ago=75,
    ),
    # ---------------------------------------------------------------- Bangles
    ProductSpec(
        "classic-kada",
        "Classic Kada",
        "bangles",
        "22K",
        "bangle",
        [
            VariantSpec(
                "ANV-BG-001",
                label="Size 2.4",
                size="2.4",
                gross=D("18.200"),
                net=D("18.200"),
                stock=2,
            ),
            VariantSpec(
                "ANV-BG-002",
                label="Size 2.6",
                size="2.6",
                gross=D("19.100"),
                net=D("19.100"),
                stock=3,
                default=True,
            ),
            VariantSpec(
                "ANV-BG-003",
                label="Size 2.8",
                size="2.8",
                gross=D("20.000"),
                net=D("20.000"),
                stock=1,
            ),
        ],
        "A solid, rounded kada with a mirror finish.",
        making=("percent", D("10")),
        collections=["everyday-gold"],
        attrs={"occasion": "everyday", "style": "traditional"},
        bestseller=True,
        published_days_ago=180,
    ),
    ProductSpec(
        "filigree-bangle-pair",
        "Filigree Bangle Pair",
        "bangles",
        "22K",
        "bangle",
        [
            VariantSpec(
                "ANV-BG-004",
                label="Size 2.4 (pair)",
                size="2.4",
                gross=D("26.400"),
                net=D("26.000"),
                stock=1,
            ),
            VariantSpec(
                "ANV-BG-005",
                label="Size 2.6 (pair)",
                size="2.6",
                gross=D("27.600"),
                net=D("27.200"),
                stock=1,
                default=True,
            ),
        ],
        "A pair of openwork filigree bangles.",
        making=("percent", D("17")),
        wastage=D("3"),
        collections=["bridal-heirlooms"],
        attrs={"occasion": "wedding", "style": "traditional"},
        featured=True,
        published_days_ago=25,
    ),
    ProductSpec(
        "slim-stacking-bangle",
        "Slim Stacking Bangle",
        "bangles",
        "18K",
        "bangle",
        [
            VariantSpec(
                "ANV-BG-006",
                label="Size 2.6",
                size="2.6",
                gross=D("5.400"),
                net=D("5.400"),
                stock=8,
                default=True,
            )
        ],
        "A thin bangle made for stacking.",
        making=("per_gram", D("650")),
        colour="rose",
        collections=["everyday-gold"],
        attrs={"occasion": "office", "style": "minimal"},
        published_days_ago=6,
    ),
    ProductSpec(
        "diamond-line-bangle",
        "Diamond Line Bangle",
        "bangles",
        "18K",
        "bangle",
        [
            VariantSpec(
                "ANV-BG-007",
                label="Size 2.6",
                size="2.6",
                gross=D("9.800"),
                net=D("9.300"),
                stone_ct=D("0.50"),
                stone_value=D("42000.00"),
                stock=1,
                default=True,
            )
        ],
        "A row of small stones set along a slim bangle.",
        colour="white",
        making=("percent", D("18")),
        collections=["minimal-diamonds"],
        attrs={"occasion": "festive", "style": "contemporary"},
        stone_details=SAMPLE_STONE_NOTE,
        published_days_ago=50,
    ),
    # ---------------------------------------------------------------- Bracelets
    ProductSpec(
        "curb-link-bracelet",
        "Curb Link Bracelet",
        "bracelets",
        "22K",
        "bracelet",
        [
            VariantSpec(
                "ANV-BR-001",
                label="7 inch",
                size="7in",
                gross=D("9.400"),
                net=D("9.400"),
                stock=4,
                default=True,
            ),
            VariantSpec(
                "ANV-BR-002",
                label="8 inch",
                size="8in",
                gross=D("10.700"),
                net=D("10.700"),
                stock=2,
            ),
        ],
        "A flat curb link bracelet with a secure box clasp.",
        making=("per_gram", D("500")),
        collections=["everyday-gold"],
        attrs={"occasion": "everyday", "style": "contemporary"},
        published_days_ago=100,
    ),
    ProductSpec(
        "tennis-bracelet",
        "Tennis Bracelet",
        "bracelets",
        "18K",
        "bracelet",
        [
            VariantSpec(
                "ANV-BR-003",
                label="7 inch",
                size="7in",
                gross=D("8.900"),
                net=D("8.100"),
                stone_ct=D("1.00"),
                stone_value=D("86000.00"),
                stock=1,
                default=True,
            )
        ],
        "A continuous line of small stones.",
        colour="white",
        making=("percent", D("20")),
        collections=["minimal-diamonds", "bridal-heirlooms"],
        attrs={"occasion": "wedding", "style": "contemporary"},
        featured=True,
        stone_details=SAMPLE_STONE_NOTE,
        published_days_ago=35,
    ),
    ProductSpec(
        "charm-bracelet",
        "Charm Bracelet",
        "bracelets",
        "14K",
        "bracelet",
        [VariantSpec("ANV-BR-004", fixed=D("21500.00"), gross=D("4.200"), stock=3, default=True)],
        "A fine chain with three small charms; priced as a finished piece.",
        model="fixed",
        making=("none", D("0")),
        colour="rose",
        attrs={"occasion": "everyday", "style": "contemporary"},
        published_days_ago=9,
    ),
    ProductSpec(
        "nazariya-baby-bracelet",
        "Nazariya Baby Bracelet",
        "bracelets",
        "22K",
        "bracelet",
        [
            VariantSpec(
                "ANV-BR-005",
                gross=D("3.600"),
                net=D("3.400"),
                other=D("250.00"),
                other_label="Black bead strand",
                stock=5,
                default=True,
            )
        ],
        "A small bracelet with black beads and gold links.",
        making=("per_gram", D("650")),
        attrs={"occasion": "everyday", "style": "traditional"},
        published_days_ago=220,
    ),
    # ---------------------------------------------------------------- Chains
    ProductSpec(
        "rope-chain",
        "Rope Chain",
        "chains",
        "22K",
        "chain",
        [
            VariantSpec(
                "ANV-CH-001",
                label="18 inch",
                size="18in",
                gross=D("8.000"),
                net=D("8.000"),
                stock=6,
                default=True,
            ),
            VariantSpec(
                "ANV-CH-002",
                label="20 inch",
                size="20in",
                gross=D("8.900"),
                net=D("8.900"),
                stock=4,
            ),
            VariantSpec(
                "ANV-CH-003",
                label="22 inch",
                size="22in",
                gross=D("9.800"),
                net=D("9.800"),
                stock=0,
            ),
        ],
        "A classic twisted rope chain.",
        making=("per_gram", D("450")),
        collections=["everyday-gold"],
        attrs={"occasion": "everyday", "style": "traditional"},
        bestseller=True,
        published_days_ago=400,
    ),
    ProductSpec(
        "box-chain",
        "Box Chain",
        "chains",
        "18K",
        "chain",
        [
            VariantSpec(
                "ANV-CH-004",
                label="18 inch",
                size="18in",
                gross=D("4.200"),
                net=D("4.200"),
                stock=7,
                default=True,
            )
        ],
        "A fine box chain that pairs with any pendant.",
        colour="white",
        making=("per_gram", D("500")),
        collections=["everyday-gold"],
        attrs={"occasion": "office", "style": "minimal"},
        published_days_ago=15,
    ),
    ProductSpec(
        "figaro-chain",
        "Figaro Chain",
        "chains",
        "22K",
        "chain",
        [
            VariantSpec(
                "ANV-CH-005",
                label="20 inch",
                size="20in",
                gross=D("12.500"),
                net=D("12.500"),
                stock=2,
                default=True,
            )
        ],
        "Alternating long and short links in solid gold.",
        making=("per_gram", D("480")),
        attrs={"occasion": "everyday", "style": "contemporary"},
        published_days_ago=45,
    ),
    ProductSpec(
        "twisted-singapore-chain",
        "Twisted Singapore Chain",
        "chains",
        "24K",
        "chain",
        [
            VariantSpec(
                "ANV-CH-006",
                label="18 inch",
                size="18in",
                gross=D("5.000"),
                net=D("5.000"),
                stock=3,
                default=True,
            )
        ],
        "A sparkling twisted chain in high-purity gold.",
        making=("percent", D("8")),
        attrs={"occasion": "festive", "style": "minimal"},
        published_days_ago=2,
    ),
    # ---------------------------------------------------------------- Mangalsutra
    ProductSpec(
        "classic-vati-mangalsutra",
        "Classic Vati Mangalsutra",
        "mangalsutra",
        "22K",
        "mangalsutra",
        [
            VariantSpec(
                "ANV-MS-001",
                label="24 inch",
                size="24in",
                gross=D("14.300"),
                net=D("13.600"),
                other=D("400.00"),
                other_label="Black bead strands",
                stock=3,
                default=True,
            )
        ],
        "Twin vati pendant on double black-bead strands.",
        making=("percent", D("12")),
        wastage=D("2"),
        collections=["bridal-heirlooms"],
        attrs={"occasion": "wedding", "style": "traditional"},
        bestseller=True,
        published_days_ago=160,
    ),
    ProductSpec(
        "modern-mangalsutra-bracelet",
        "Modern Mangalsutra Bracelet",
        "mangalsutra",
        "18K",
        "bracelet",
        [
            VariantSpec(
                "ANV-MS-002",
                gross=D("3.800"),
                net=D("3.500"),
                other=D("150.00"),
                other_label="Black bead strand",
                stock=4,
                default=True,
            )
        ],
        "A contemporary mangalsutra worn on the wrist.",
        making=("flat", D("2200")),
        collections=["everyday-gold"],
        attrs={"occasion": "everyday", "style": "contemporary"},
        published_days_ago=18,
    ),
    ProductSpec(
        "solitaire-mangalsutra",
        "Solitaire Mangalsutra",
        "mangalsutra",
        "18K",
        "mangalsutra",
        [
            VariantSpec(
                "ANV-MS-003",
                label="18 inch",
                size="18in",
                gross=D("6.600"),
                net=D("6.300"),
                stone_ct=D("0.30"),
                stone_value=D("24000.00"),
                other=D("200.00"),
                other_label="Black bead strands",
                stock=1,
                default=True,
            )
        ],
        "A single stone pendant on a fine black-bead chain.",
        colour="white",
        making=("percent", D("16")),
        collections=["minimal-diamonds", "bridal-heirlooms"],
        attrs={"occasion": "wedding", "style": "minimal"},
        stone_details=SAMPLE_STONE_NOTE,
        published_days_ago=28,
    ),
]

# Automatic discount used to exercise the pricing engine in development.
SAMPLE_DISCOUNT = {
    "name": "10% off making charges — Everyday Gold (sample offer)",
    "kind": "percent_off_making",
    "value": D("10"),
    "scope": "collection",
    "collection_slug": "everyday-gold",
}
