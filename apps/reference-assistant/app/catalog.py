"""A small seeded fashion catalog standing in for a real production one.
Several pairs are deliberately near-duplicate (same category, similar
wording) so ENABLE_RETRIEVAL_BUG can reproduce a realistic retrieval
failure: the retrieval step quietly substituting one variant's listing for
a visually or textually similar one."""

CATALOG: list[dict] = [
    {
        "sku": "BPS-2214",
        "name": "Rajasthani block-print saree",
        "listing_text": (
            "SKU BPS-2214 — Rajasthani block-print saree. Fabric: pure mulberry silk. "
            "Care: dry clean only. Do not machine wash or hand wash; both can damage "
            "the fabric and the block-print dye."
        ),
        "confusable_with": "COT-5501",
    },
    {
        "sku": "COT-5501",
        "name": "Cotton block-print saree",
        "listing_text": (
            "SKU COT-5501 — Cotton block-print saree. Fabric: 100% cotton. "
            "Care: machine-wash cold, tumble dry low."
        ),
        "confusable_with": "BPS-2214",
    },
    {
        "sku": "BPS-2231",
        "name": "Indigo block-print saree",
        "listing_text": (
            "SKU BPS-2231 — Indigo block-print saree. Fabric: pure mulberry silk. "
            "Care: dry clean only. Hand-washing, even in cold water, will damage this piece."
        ),
        "confusable_with": None,
    },
    {
        "sku": "DUP-3390",
        "name": "Teal cotton dupatta",
        "listing_text": (
            "SKU DUP-3390 — Teal cotton dupatta. Fabric: cotton with reactive dye. "
            "Care: hand-wash separately, colour may run. Do not machine wash with other items."
        ),
        "confusable_with": "DUP-3391",
    },
    {
        "sku": "DUP-3391",
        "name": "Plain white dupatta",
        "listing_text": (
            "SKU DUP-3391 — Plain white cotton dupatta. Fabric: cotton, undyed. "
            "Care: machine-wash cold, safe with other items."
        ),
        "confusable_with": "DUP-3390",
    },
    {
        "sku": "KUR-1042",
        "name": "Easy-care cotton kurta",
        "listing_text": (
            "SKU KUR-1042 — Easy-care cotton-blend kurta. Fabric: easy-care cotton blend. "
            "Care: machine-wash cold, tumble dry low."
        ),
        "confusable_with": None,
    },
    {
        "sku": "LIN-2207",
        "name": "Linen trousers",
        "listing_text": (
            "SKU LIN-2207 — Linen trousers. Fabric: 100% linen. "
            "Care: dry clean recommended. Avoid direct sunlight when drying."
        ),
        "confusable_with": None,
    },
    {
        "sku": "FTW-1187",
        "name": "Running shoes (standard fit)",
        "listing_text": (
            "SKU FTW-1187 — Running shoes, standard fit. Sizing: full sizes only "
            "(no half sizes stocked for this model)."
        ),
        "confusable_with": "FTW-1188",
    },
    {
        "sku": "FTW-1188",
        "name": "Running shoes (wide fit)",
        "listing_text": (
            "SKU FTW-1188 — Running shoes, wide fit. Sizing: available in half sizes."
        ),
        "confusable_with": "FTW-1187",
    },
    {
        "sku": "JKT-6601",
        "name": "All-weather outerwear jacket",
        "listing_text": (
            "SKU JKT-6601 — All-weather outerwear jacket. Rated water-resistant, not "
            "suitable for heavy rain — it is not fully waterproof."
        ),
        "confusable_with": None,
    },
    {
        "sku": "EMB-DUP-410",
        "name": "Embroidered dupatta",
        "listing_text": (
            "SKU EMB-DUP-410 — Embroidered dupatta. Fabric: silk-blend with embroidery. "
            "Care: hand-wash cold, separately."
        ),
        "confusable_with": None,
    },
    {
        "sku": "REG-SIZE-ADULT",
        "name": "Regional size chart — adult kurtas, blouses, sarees",
        "listing_text": (
            "Regional adult size conversion table (kurtas, blouses, sarees): regional "
            "sizing uses its own numbering scale, distinct from the national chart, "
            "for chest measurement and garment length."
        ),
        "confusable_with": "REG-SIZE-KIDS",
    },
    {
        "sku": "REG-SIZE-KIDS",
        "name": "Regional size chart — children's kurtas",
        "listing_text": (
            "Regional children's size conversion table (kurtas): children's regional "
            "sizing uses an entirely separate numbering scheme from the adult regional "
            "chart — a children's size number does not correspond to the same number "
            "on the adult scale."
        ),
        "confusable_with": "REG-SIZE-ADULT",
    },
    {
        "sku": "POLICY-FESTIVE-SALE",
        "name": "Festive sale — bundle discount and gift-wrap policy",
        "listing_text": (
            "Festive sale terms: the three-item bundle discount cannot be combined "
            "with any festive sale coupon code — coupons and bundle pricing do not "
            "stack. Gift wrap add-on costs a flat fee per bundle and covers wrapping "
            "paper, ribbon, and a printed gift tag; it does not include a greeting card."
        ),
        "confusable_with": None,
    },
]


def get_catalog_entry(sku: str) -> dict | None:
    return next((item for item in CATALOG if item["sku"] == sku), None)
