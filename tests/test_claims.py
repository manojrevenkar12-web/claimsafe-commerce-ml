"""The register and the checker: what may be said about which product."""

from __future__ import annotations

import yaml

from claimsafe.checker import Checker, sentences
from claimsafe.register import load_register
from claimsafe.settings import ROOT


def test_register_is_internally_consistent():
    reg = load_register()
    assert len(reg.claims) == 106
    assert len({c.id for c in reg.claims}) == len(reg.claims)
    for c in reg.claims:
        assert c.nutrient in reg.nutrients or c.nutrient == "epa_dha"
        if c.kind == "min_daily":
            assert c.amounts


def test_source_condition_is_fifteen_percent_of_the_nrv():
    reg = load_register()
    claim = next(c for c in reg.claims if c.text == "Zinc contributes to the maintenance of normal hair")
    assert reg.condition_met(claim, {"zinc": 1.5})[0]  # exactly 15% of 10 mg
    assert not reg.condition_met(claim, {"zinc": 1.49})[0]
    assert not reg.condition_met(claim, {})[0]


def test_omega_claims_need_daily_amounts_and_are_not_for_children():
    reg = load_register()
    bp = next(c for c in reg.claims if "blood pressure" in c.text)
    assert reg.condition_met(bp, {"epa": 1800, "dha": 1200})[0]
    assert not reg.condition_met(bp, {"epa": 1800, "dha": 1100})[0]
    assert not reg.condition_met(bp, {"epa": 1800, "dha": 1200}, for_children=True)[0]


def test_verdicts(ck, products):
    v = lambda pid, text: ck.check(text, products[pid]).verdict
    assert v("P05", "Magnesium contributes to a reduction of tiredness and fatigue.") == "ok"
    assert v("P07", "Magnesium contributes to a reduction of tiredness and fatigue.") == "block"  # 40 mg = 11% NRV
    assert v("P01", "Vitamin D boosts your immune system.") == "rewrite"
    assert v("P01", "Vitamin D prevents colds and flu.") == "block"
    assert v("P28", "Ashwagandha lowers cortisol.") == "block"
    assert v("P30", "Shade-grown matcha from Japan.") == "ok"
    assert v("P26", "Vitamin C, zinc and vitamin D contribute to the normal function of the immune system.") == "ok"
    assert v("P13", "Zinc and selenium contribute to the normal function of the immune system.") == "block"


def test_required_statement_is_added(ck, products):
    rep = ck.check("DHA contributes to maintenance of normal brain function.", products["P21"])
    assert rep.verdict == "rewrite"
    assert "250 mg of DHA" in rep.findings[0].suggestion
    full = rep.findings[0].suggestion
    assert ck.check(full, products["P21"]).verdict == "ok"


def test_every_rewrite_is_register_text_and_passes_the_checker(ck, products):
    reg_texts = {c.text for c in load_register().claims} | {c.statement for c in load_register().claims if c.statement}
    for p in products.values():
        rep = ck.check(p.marketing, p)
        for f in rep.findings:
            if f.verdict == "rewrite":
                for s in sentences(f.suggestion):
                    assert s.rstrip(".") in reg_texts, s
        assert ck.check(rep.safe_text(), p).verdict == "ok" if rep.safe_text() else True


def test_dev_set_has_no_errors(ck, products):
    items = yaml.safe_load((ROOT / "data" / "eval" / "dev.yaml").read_text())["items"]
    wrong = [i for i in items if (ck.check(i["text"], products[i["product"]]).verdict == "ok") != i["allowed"]]
    assert wrong == []


def test_an_approved_paraphrase_counts_as_authorised(products):
    ck = Checker()
    ck.pol.approved["vitamin d supports your immune system"] = "C006"
    try:
        assert ck.check("Vitamin D supports your immune system.", products["P01"]).verdict == "ok"
        assert ck.check("Vitamin D supports your immune system.", products["P04"]).verdict == "block"
    finally:
        ck.pol.approved.pop("vitamin d supports your immune system")


def test_checker_settings_are_those_of_the_held_out_run():
    from claimsafe.settings import load

    c = load().claims
    assert (c.register_file, c.paraphrases, c.min_rewrite_similarity) == (
        "data/claims/register.yaml",
        "data/claims/paraphrases.yaml",
        0.45,
    )
