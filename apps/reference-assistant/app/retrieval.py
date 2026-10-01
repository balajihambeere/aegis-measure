import re

from app.catalog import CATALOG, get_catalog_entry

_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> set[str]:
    return set(_WORD_RE.findall(text.lower()))


def _score(question: str, question_tokens: set[str], item: dict) -> int:
    item_tokens = _tokenize(item["name"] + " " + item["listing_text"] + " " + item["sku"])
    score = len(question_tokens & item_tokens)
    if item["sku"].lower() in question.lower():
        score += 5
    return score


def retrieve(question: str, enable_retrieval_bug: bool) -> dict:
    """Simple word-overlap retrieval over the seeded catalog — deliberately
    unsophisticated (no vector index) since the point is to demonstrate the
    component-vs-end-to-end distinction, not to showcase retrieval technique.
    Mentioning a SKU directly in the question is a strong signal and
    outweighs ordinary word overlap.

    When ENABLE_RETRIEVAL_BUG is set, the best match is silently swapped for
    its declared near-duplicate twin — reproducing a routine reindex that
    started confusing visually/textually similar items, without needing an
    actual search index to misbehave."""
    question_tokens = _tokenize(question)
    best = max(CATALOG, key=lambda item: _score(question, question_tokens, item))

    if enable_retrieval_bug and best.get("confusable_with"):
        twin = get_catalog_entry(best["confusable_with"])
        if twin is not None:
            return twin

    return best
