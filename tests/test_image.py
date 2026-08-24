import app.routers.image as image_module


def test_image_returns_png_and_caches_to_disk(client, monkeypatch, tmp_path):
    monkeypatch.setattr(image_module, "CACHE_DIR", tmp_path)

    calls = []

    def fake_generate_image(description):
        calls.append(description)
        return b"FAKE_PNG_BYTES"

    monkeypatch.setattr(image_module, "generate_image", fake_generate_image)

    res = client.post("/api/image", json={"description": "A man giving a presentation."})
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"
    assert res.content == b"FAKE_PNG_BYTES"
    assert len(calls) == 1

    # second request for the SAME description should hit the on-disk cache,
    # not call the OpenAI service again
    res2 = client.post("/api/image", json={"description": "A man giving a presentation."})
    assert res2.status_code == 200
    assert res2.content == b"FAKE_PNG_BYTES"
    assert len(calls) == 1


def test_image_without_api_key_returns_503(client, monkeypatch, tmp_path):
    monkeypatch.setattr(image_module, "CACHE_DIR", tmp_path)

    def raise_runtime(description):
        raise RuntimeError("OpenAI API Key 尚未設定。")

    monkeypatch.setattr(image_module, "generate_image", raise_runtime)

    res = client.post("/api/image", json={"description": "some unique description not cached elsewhere"})
    assert res.status_code == 503


def test_image_rejects_empty_description(client):
    res = client.post("/api/image", json={"description": ""})
    assert res.status_code == 422
