"""Product registry. Every folder in kb/ that has a product.toml is one product (= one agent).

kb/<id>/product.toml   settings for that product's agent
kb/<id>/*.md           its documents
kb/<id>/eval_set.json  its test questions (optional)
index/<id>/            its vector index, built by ingest.py
"""

import tomllib
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

from config import ESCALATION_MESSAGE, INDEX_DIR, KB_DIR, MIN_SCORE, TOP_K


@dataclass(frozen=True)
class Product:  # pylint: disable=too-many-instance-attributes  # one field per product.toml key
    id: str  # folder name, e.g. "kettle"
    name: str  # display name, e.g. "Kettlewise K2"
    description: str  # what the router reads to pick this product
    persona: str  # first line of the agent's system prompt
    subject: str  # "If a question is unrelated to <subject> ..."
    general_scope: str  # "... even if you believe it is true for <general_scope>"
    example_no: str  # example of a "No" that IS answered from the docs
    example_missing: str  # example of a question the docs don't cover
    brand: str = ""
    tagline: str = ""
    top_k: int = TOP_K
    min_score: float = MIN_SCORE
    escalation_message: str = ESCALATION_MESSAGE
    # General-knowledge fallback (off unless the product turns it on)
    general_fallback: bool = False
    general_topic: str = ""
    general_notice: str = ""
    # Web UI
    welcome: str = ""
    suggestions: list[str] = field(default_factory=list)
    specs: list[list[str]] = field(default_factory=list)
    contact_label: str = ""
    contact_text: str = ""
    contact_href: str = ""

    @property
    def kb_dir(self) -> Path:
        return Path(KB_DIR) / self.id

    @property
    def index_dir(self) -> Path:
        return Path(INDEX_DIR) / self.id

    @property
    def eval_path(self) -> Path:
        return self.kb_dir / "eval_set.json"

    def public(self) -> dict:
        """What the web UI needs to show this product."""
        return {
            "id": self.id,
            "name": self.name,
            "brand": self.brand,
            "tagline": self.tagline,
            "welcome": self.welcome,
            "suggestions": self.suggestions,
            "specs": self.specs,
            "contact_label": self.contact_label,
            "contact_text": self.contact_text,
            "contact_href": self.contact_href,
            "general_fallback": self.general_fallback,
        }


def load_products() -> dict[str, Product]:
    products = {}
    for path in sorted(Path(KB_DIR).glob("*/product.toml")):
        settings = tomllib.loads(path.read_text(encoding="utf-8"))
        try:
            product = Product(id=path.parent.name, **settings)
        except TypeError as e:  # a missing or misspelled key
            raise ValueError(f"{path}: {e}") from None
        if product.general_fallback and not (product.general_topic and product.general_notice):
            raise ValueError(f"{path}: general_fallback needs general_topic and general_notice")
        products[product.id] = product
    if not products:
        raise FileNotFoundError(f"No products found. Expected {KB_DIR}/<product>/product.toml")
    return products


PRODUCTS = load_products()


def get_product(product_id: str) -> Product:
    if product_id not in PRODUCTS:
        raise KeyError(f"Unknown product '{product_id}'. Available: {', '.join(PRODUCTS)}")
    return PRODUCTS[product_id]


@cache
def get_store(product_id: str):
    """Load a product's index once, the first time it is searched."""
    # Imported here so that just listing products doesn't load numpy and the index code.
    from vector_store import VectorStore  # pylint: disable=import-outside-toplevel

    product = get_product(product_id)
    if not (product.index_dir / "vectors.npy").exists():
        raise FileNotFoundError(
            f"No index for '{product_id}'. Build it with: python ingest.py {product_id}"
        )
    return VectorStore.load(str(product.index_dir))
