from verify import parse_equation


def test_parse_equation_basic():
    parsed = parse_equation("6x + 20 + 10x = 48")
    assert parsed.parse_valid is True
    assert parsed.normalized == "6x+20+10x=48"


def test_parse_equation_invalid_without_equal():
    parsed = parse_equation("16x+20")
    assert parsed.parse_valid is False
