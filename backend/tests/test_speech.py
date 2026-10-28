"""Exercise teammate transcription routes without downloading a model or recording audio."""
from app.services import speech


def available(monkeypatch):
    monkeypatch.setattr(speech, 'status', lambda: {'available': True, 'runs_locally': True})


def test_speech_status_and_transcription_auth(anon_client, monkeypatch):
    available(monkeypatch)
    assert anon_client.get('/api/speech').json()['available'] is True
    assert anon_client.post('/api/speech/transcribe', content=b'fixture', headers={'content-type': 'audio/webm'}).status_code == 401


def test_optional_engine_unavailable(client, monkeypatch):
    monkeypatch.setattr(speech, 'status', lambda: {'available': False})
    assert client.post('/api/speech/transcribe', content=b'fixture', headers={'content-type': 'audio/webm'}).status_code == 503


def test_audio_validation(client, monkeypatch):
    available(monkeypatch)
    monkeypatch.setattr(speech, 'MAX_AUDIO_BYTES', 8)
    assert client.post('/api/speech/transcribe', content=b'x', headers={'content-type': 'text/plain'}).status_code == 415
    assert client.post('/api/speech/transcribe', content=b'', headers={'content-type': 'audio/webm'}).status_code == 422
    assert client.post('/api/speech/transcribe', content=b'x'*9, headers={'content-type': 'audio/webm'}).status_code == 413


def test_local_transcription_language_and_response(client, monkeypatch):
    available(monkeypatch)
    monkeypatch.setattr(speech, 'MODEL', 'base')
    calls = []
    monkeypatch.setattr(speech, 'transcribe', lambda audio, lang: calls.append((audio, lang)) or 'Synthetic dictation fixture.')
    response = client.post('/api/speech/transcribe?lang=hi-IN', content=b'fixture', headers={'content-type': 'audio/webm'})
    assert response.json() == {'text': 'Synthetic dictation fixture.'}
    assert calls == [(b'fixture', 'hi')]
    monkeypatch.setattr(speech, 'MODEL', 'base.en')
    assert client.post('/api/speech/transcribe?lang=en-US', content=b'fixture', headers={'content-type': 'audio/webm'}).status_code == 200
    assert calls[-1] == (b'fixture', None)
