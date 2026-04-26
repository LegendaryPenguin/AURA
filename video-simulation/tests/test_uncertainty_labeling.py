from narrate import run_stage as narrate_stage


def test_uncertainty_labels_present_in_draft_mode():
    normalized = {"normalized_steps": ["6x+20+10x=48"], "quality_scores": [0.8]}
    verified = {
        "is_verified": False,
        "uncertainty_reasons": ["symbolic_verification_incomplete"],
        "transitions": [],
    }
    narrate = narrate_stage(normalized, verified)
    assert narrate["draft_mode"] is True
    assert "symbolic_verification_incomplete" in narrate["uncertainty_reasons"]
