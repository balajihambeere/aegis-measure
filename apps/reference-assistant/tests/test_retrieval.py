"""Retrieval has to actually find the right listing on its own — and, with
the bug flag on, reproduce a realistic near-duplicate-SKU confusion."""

from app.retrieval import retrieve


def test_retrieve_finds_item_by_explicit_sku_mention():
    item = retrieve("Does SKU BPS-2214 need dry cleaning?", enable_retrieval_bug=False)
    assert item["sku"] == "BPS-2214"


def test_retrieve_finds_dupatta_by_keyword_overlap():
    item = retrieve(
        "Can I machine wash the teal cotton dupatta?", enable_retrieval_bug=False
    )
    assert item["sku"] == "DUP-3390"


def test_retrieval_bug_substitutes_the_near_duplicate_twin():
    """Asking about the teal dupatta's wash instructions should return the
    plain white dupatta's listing instead, once the bug flag is enabled."""
    without_bug = retrieve(
        "Does the teal cotton dupatta DUP-3390 need hand washing?", enable_retrieval_bug=False
    )
    assert without_bug["sku"] == "DUP-3390"

    with_bug = retrieve(
        "Does the teal cotton dupatta DUP-3390 need hand washing?", enable_retrieval_bug=True
    )
    assert with_bug["sku"] == "DUP-3391"


def test_retrieval_bug_has_no_effect_on_items_with_no_confusable_twin():
    item = retrieve("How should I dry clean my linen trousers?", enable_retrieval_bug=True)
    assert item["sku"] == "LIN-2207"
