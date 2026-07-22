import json
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_source_coverage_contract_is_strict():
    policy = json.loads((ROOT / "health/source-coverage.json").read_text())
    assert policy["thresholds"]["record_count_coverage"] >= 0.99
    assert policy["thresholds"]["identifier_row_coverage"] >= 0.99
    assert policy["thresholds"]["mapped_cell_coverage"] >= 0.75


def test_ontology_policy_caps_local_vocabulary():
    policy = json.loads((ROOT / "health/ontology-policy.json").read_text())
    assert len(policy["allowed_classes"]) <= 2
    assert len(policy["allowed_predicates"]) <= 5
    assert policy["min_score"] >= 80
