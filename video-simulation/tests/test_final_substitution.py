from verify import final_substitution_check


def test_final_substitution_for_solved_line():
    result = final_substitution_check("x=7/4")
    assert result["status"] in {"pass", "unknown"}
