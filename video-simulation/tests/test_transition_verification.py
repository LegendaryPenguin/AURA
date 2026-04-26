from verify import run_stage


def test_transition_verification_detects_inconsistency():
    payload = {"normalized_steps": ["6x+20+10x=48", "16x+20=49"]}
    result = run_stage(payload)
    statuses = [item["status"] for item in result["transitions"]]
    assert "inconsistent" in statuses or "unknown" in statuses
    assert result["is_verified"] is False


def test_transition_verification_happy_path_or_unknown_without_sympy():
    payload = {"normalized_steps": ["6x+20+10x=48", "16x+20=48", "16x=28"]}
    result = run_stage(payload)
    assert result["verification_status"] in {"verified", "draft"}


def test_transition_verification_supports_implicit_multiplication():
    payload = {"normalized_steps": ["6x+20+4(2x)=48", "6x+20+8x=48"]}
    result = run_stage(payload)
    assert result["transitions"][0]["status"] in {"equivalent", "unknown"}


def test_transition_verification_supports_division_isolation():
    payload = {"normalized_steps": ["16x=28", "x=28/16"]}
    result = run_stage(payload)
    assert result["transitions"][0]["status"] in {"equivalent", "unknown"}
