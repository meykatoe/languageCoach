// Listening-item audio playback: server-side OpenAI TTS (with disk cache)
// via /api/tts, falling back to the browser's built-in speech synthesis
// when that call fails (no API key, network error, ...).

const SPEAK_LABEL = '播放語音';
const SPEAK_LOADING_LABEL = '語音生成中...';
const SPEAK_PLAYING_LABEL = '播放中...';

function playWithBrowserTts(text, btn, resetLabel) {
  if (!('speechSynthesis' in window)) {
    resetLabel();
    return;
  }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'en-US';
  utterance.rate = 0.95;
  btn.textContent = SPEAK_PLAYING_LABEL;
  utterance.onend = utterance.onerror = resetLabel;
  window.speechSynthesis.speak(utterance);
}

function addSpeakButton(text, container) {
  const btn = el('button', { class: 'secondary speak-btn', html: iconHtml('speaker') + SPEAK_LABEL });
  let cachedAudioUrl = null;

  const resetLabel = () => {
    btn.disabled = false;
    btn.innerHTML = iconHtml('speaker') + SPEAK_LABEL;
  };

  const playUrl = (url) => {
    const audio = new Audio(url);
    btn.textContent = SPEAK_PLAYING_LABEL;
    audio.onended = audio.onerror = resetLabel;
    audio.play().catch(resetLabel); // play() can reject (autoplay policy, no output device, ...)
  };

  btn.addEventListener('click', async () => {
    btn.disabled = true;

    if (cachedAudioUrl) {
      playUrl(cachedAudioUrl);
      return;
    }

    btn.textContent = SPEAK_LOADING_LABEL;
    try {
      const res = await fetch('/api/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });
      if (!res.ok) {
        playWithBrowserTts(text, btn, resetLabel);
        return;
      }
      const blob = await res.blob();
      cachedAudioUrl = URL.createObjectURL(blob);
      playUrl(cachedAudioUrl);
    } catch (err) {
      playWithBrowserTts(text, btn, resetLabel);
    }
  });

  container.appendChild(btn);
}
