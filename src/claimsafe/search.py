"""Product search that can only surface what the shop may lawfully say.

Three retrievers over the same catalogue:
  marketing  BM25 over the product name and marketing copy (what most shop search indexes)
  claims     BM25 over the product name and the authorised claims its composition makes it eligible for
  hybrid     claims BM25 fused with dense LSA vectors in a FAISS inner-product index

Dense vectors come from TF-IDF + truncated SVD fitted on the catalogue, because this repository has no access to a
hosted embedding model; `Embedder` is the seam where Vertex AI text embeddings would plug in.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

import faiss
import numpy as np
from rank_bm25 import BM25Okapi
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer

from claimsafe.catalog import Product, load_catalog
from claimsafe.checker import load_policy
from claimsafe.register import Register, load_register
from claimsafe.settings import Settings, load

# A topic is relevant to a product when one of its eligible claims contains one of these phrases.
TOPICS: dict[str, tuple[str, ...]] = {
    "tiredness": ("tiredness and fatigue",),
    "immune": ("immune system",),
    "bones": ("normal bones",),
    "hair": ("normal hair",),
    "skin": ("normal skin", "function of skin"),
    "nails": ("normal nails",),
    "heart": ("function of the heart",),
    "brain": ("brain function", "cognitive function"),
    "vision": ("normal vision",),
    "muscle": ("muscle function",),
    "thyroid": ("thyroid",),
    "pregnancy": ("during pregnancy",),
    "blood": ("red blood cell", "haemoglobin", "blood formation"),
    "psychological": ("psychological function", "nervous system"),
    "energy": ("energy-yielding metabolism",),
    "teeth": ("normal teeth", "function of teeth"),
}

TOKEN = re.compile(r"[a-z0-9]+")


def tokens(text: str) -> list[str]:
    syn = load_policy().synonyms
    out = []
    for w in TOKEN.findall(text.lower()):
        w = syn.get(w, w)
        if len(w) > 4 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        out.append(w)
    return out


class Embedder(Protocol):
    def fit(self, docs: list[str]) -> None: ...
    def embed(self, texts: list[str]) -> np.ndarray: ...


class LsaEmbedder:
    def __init__(self, components: int, seed: int = 0):
        self.vec = TfidfVectorizer(tokenizer=tokens, lowercase=False, token_pattern=None, sublinear_tf=True)
        self.components = components
        self.seed = seed

    def fit(self, docs: list[str]) -> None:
        x = self.vec.fit_transform(docs)
        k = max(2, min(self.components, x.shape[1] - 1, x.shape[0] - 1))
        self.svd = TruncatedSVD(n_components=k, random_state=self.seed).fit(x)

    def embed(self, texts: list[str]) -> np.ndarray:
        z = self.svd.transform(self.vec.transform(texts)).astype("float32")
        faiss.normalize_L2(z)
        return z


def claims_view(p: Product, reg: Register) -> str:
    claims = p.eligible_claims(reg)
    return " ".join([p.name, p.category, *[c.text for c in claims]])


def relevant(p: Product, topic: str, reg: Register) -> bool:
    texts = [c.text.lower() for c in p.eligible_claims(reg)]
    return any(ph in t for t in texts for ph in TOPICS[topic])


@dataclass(frozen=True)
class Hit:
    product: Product
    score: float


class Search:
    def __init__(self, products: tuple[Product, ...] | None = None, settings: Settings | None = None):
        self.s = settings or load()
        self.reg = load_register()
        self.products = products or load_catalog()
        self.marketing_docs = [f"{p.name} {p.category} {p.marketing}" for p in self.products]
        self.claims_docs = [claims_view(p, self.reg) for p in self.products]
        self.bm25_marketing = BM25Okapi([tokens(d) for d in self.marketing_docs])
        self.bm25_claims = BM25Okapi([tokens(d) for d in self.claims_docs])
        self.embedder = LsaEmbedder(self.s.search.lsa_components)
        self.embedder.fit(self.claims_docs)
        vecs = self.embedder.embed(self.claims_docs)
        self.index = faiss.IndexIDMap(faiss.IndexFlatIP(vecs.shape[1]))
        self.index.add_with_ids(vecs, np.arange(len(self.products), dtype="int64"))

    def _rank(self, scores: np.ndarray, k: int) -> list[Hit]:
        order = np.argsort(-scores, kind="stable")[:k]
        return [Hit(self.products[i], float(scores[i])) for i in order if scores[i] > 0]

    def search(self, query: str, method: str = "hybrid", k: int | None = None) -> list[Hit]:
        k = k or self.s.search.k
        q = tokens(query)
        if method == "marketing":
            return self._rank(np.asarray(self.bm25_marketing.get_scores(q)), k)
        sparse = np.asarray(self.bm25_claims.get_scores(q), dtype=float)
        if method == "claims":
            return self._rank(sparse, k)
        if method != "hybrid":
            raise ValueError(f"unknown method {method}")
        dense = np.zeros(len(self.products))
        sims, ids = self.index.search(self.embedder.embed([query]), len(self.products))
        for s, i in zip(sims[0], ids[0], strict=True):
            if i >= 0:
                dense[i] = max(0.0, float(s))
        sparse_n = sparse / sparse.max() if sparse.max() > 0 else sparse
        w = self.s.search.hybrid_weight_dense
        fused = (1 - w) * sparse_n + w * dense
        # A product with no authorised claim at all has nothing lawful to say about any need.
        eligible = np.array([1.0 if p.eligible_claims(self.reg) else 0.0 for p in self.products])
        return self._rank(fused * eligible, k)


def evaluate(search: Search, queries: list[dict], k: int) -> dict:
    reg = search.reg
    out = {}
    for method in ("marketing", "claims", "hybrid"):
        rec, prec, unsafe = [], [], []
        for item in queries:
            rel = {p.id for p in search.products if relevant(p, item["topic"], reg)}
            hits = search.search(item["q"], method, k)
            got = [h.product.id for h in hits]
            rec.append(len(set(got) & rel) / min(k, len(rel)) if rel else 0.0)
            prec.append(sum(g in rel for g in got) / k)
            unsafe.append(sum(g not in rel for g in got) / max(len(got), 1))
        out[method] = {
            "recall_at_k": round(float(np.mean(rec)), 4),
            "precision_at_k": round(float(np.mean(prec)), 4),
            "results_without_a_lawful_claim_for_the_need": round(float(np.mean(unsafe)), 4),
        }
    return out
