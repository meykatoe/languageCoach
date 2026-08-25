import app.routers.tts as tts_module


def test_tts_returns_audio_and_caches_to_disk(client, monkeypatch, tmp_path):
    monkeypatch.setattr(tts_module, "CACHE_DIR", tmp_path)

    calls = []

    def fake_synthesize_speech(text, voice="alloy"):
        calls.append(text)
        return b"FAKE_MP3_BYTES"

    monkeypatch.setattr(tts_module, "synthesize_speech", fake_synthesize_speech)

    res = client.post("/api/tts", json={"text": "Hello, this is a listening transcript."})
    assert res.status_code == 200
    assert res.headers["content-type"] == "audio/mpeg"
    assert res.content == b"FAKE_MP3_BYTES"
    assert len(calls) == 1

    # second request for the SAME text should hit the on-disk cache, not
    # call the OpenAI service again
    res2 = client.post("/api/tts", json={"text": "Hello, this is a listening transcript."})
    assert res2.status_code == 200
    assert res2.content == b"FAKE_MP3_BYTES"
    assert len(calls) == 1


def test_tts_without_api_key_returns_503(client, monkeypatch, tmp_path):
    monkeypatch.setattr(tts_module, "CACHE_DIR", tmp_path)

    def raise_runtime(text, voice="alloy"):
        raise RuntimeError("OpenAI API Key 尚未設定。")

    monkeypatch.setattr(tts_module, "synthesize_speech", raise_runtime)

    res = client.post("/api/tts", json={"text": "some unique text not cached elsewhere"})
    assert res.status_code == 503


def test_tts_rejects_empty_text(client):
    res = client.post("/api/tts", json={"text": ""})
    assert res.status_code == 422
