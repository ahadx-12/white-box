from __future__ import annotations

from trustai_core.packs.tariff.evidence.retrieve import TariffEvidenceRetriever


def test_tariff_retriever_is_deterministic() -> None:
    retriever = TariffEvidenceRetriever()
    bundle_a = retriever.retrieve(
        "Athletic sneaker with textile upper and rubber outsole",
        candidate_chapters=["64"],
        top_k=8,
    )
    bundle_b = retriever.retrieve(
        "Athletic sneaker with textile upper and rubber outsole",
        candidate_chapters=["64"],
        top_k=8,
    )
    ids_a = [source.source_id for source in bundle_a]
    ids_b = [source.source_id for source in bundle_b]
    assert ids_a == ids_b
    assert any(source_id.startswith("GRI.") for source_id in ids_a)
    assert any(source_id.startswith("CH64.") for source_id in ids_a)
