from normalize import run_stage


def test_normalization_preserves_target_implicit_multiplication_form():
    vision = {
        "lines": [
            {"text": "6x + 20 + 4(2x) = 48", "confidence": 0.9},
            {"text": "6x+20+10x = 48", "confidence": 0.9},
            {"text": "16x+20 = 48", "confidence": 0.9},
            {"text": "16x = 28", "confidence": 0.9},
            {"text": "x = 28/16", "confidence": 0.9},
        ]
    }
    out = run_stage(vision)
    assert out["normalized_steps"] == [
        "6x+20+4(2x)=48",
        "6x+20+10x=48",
        "16x+20=48",
        "16x=28",
        "x=28/16",
    ]
