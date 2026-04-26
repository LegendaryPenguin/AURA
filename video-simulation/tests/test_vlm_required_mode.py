from vision_parse import run_stage


def test_vlm_required_mode_returns_error_when_endpoint_missing(monkeypatch, tmp_path):
    monkeypatch.delenv("VIDEO_SIM_VLM_ENDPOINT", raising=False)
    image_path = tmp_path / "dummy.png"
    image_path.write_bytes(b"not-an-image")
    result = run_stage(image_path=image_path)
    assert result["parse_status"] == "error"
    assert result["parser"] == "none"
