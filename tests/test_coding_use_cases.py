import json
import re

from run_scenarios import ROOT, SCENARIOS


CATALOG = ROOT / "tests/coding_use_cases.json"


def test_coding_use_case_catalog_has_unique_actionable_cases():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    cases = catalog["cases"]
    ids = [case["id"] for case in cases]
    assert len(ids) >= 25
    assert len(ids) == len(set(ids))
    assert {case["area"] for case in cases} == {
        "domain", "intake", "profile", "parameters", "method-payload",
        "response", "combined-flow", "workflow", "mock-contract",
    }
    for case in cases:
        assert re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", case["id"])
        assert case["dimensions"]
        assert case["verification"]


def test_catalog_references_existing_conversation_and_mock_scenarios():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    scenarios = json.loads(SCENARIOS.read_text(encoding="utf-8"))
    scenario_ids = {scenario["id"] for scenario in scenarios}
    mock_cases = set(catalog["mock_cases"])
    for case in catalog["cases"]:
        verification = case["verification"]
        if verification.startswith("mock:"):
            assert verification.split(":", 1)[1] in mock_cases
        else:
            assert verification in scenario_ids, case["id"]
    assert catalog["mock_cases"] == [
        "success", "browse", "list-failure", "empty-list", "missing-id",
        "malformed-list", "detail-failure", "wrong-detail-id",
        "summary-success", "summary-list-failure", "summary-invalid",
    ]


def test_catalog_pairwise_contracts_are_compatible_and_explicit():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    pairs = catalog["compatible_pairs"]
    assert len(pairs) >= 15
    assert len({tuple(pair) for pair in pairs}) == len(pairs)
    for pair in pairs:
        assert len(pair) == 2 and all(isinstance(value, str) and value for value in pair)
    dimensions = {
        (key, value)
        for case in catalog["cases"]
        for key, value in case["dimensions"].items()
        if isinstance(value, str)
    }
    for left, right in pairs:
        assert any(left in case["dimensions"].values() and right in case["dimensions"].values()
                   for case in catalog["cases"]), (left, right)
    for method in ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"):
        assert ("method", method) in dimensions
    for body in ("none", "json", "form-urlencoded", "multipart"):
        assert ("body", body) in dimensions
    for profile in ("gateway", "public", "availability", "unknown"):
        assert ("profile", profile) in dimensions


def test_catalog_does_not_claim_every_case_has_live_network_coverage():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    assert all(not case.get("real_endpoint") for case in catalog["cases"])
    assert "Do not form an unrestricted Cartesian product" in catalog["strategy"]
