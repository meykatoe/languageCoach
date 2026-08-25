// Speaking-item mic input: browser SpeechRecognition (STT), auto-appending
// the live transcript into the given textarea. Only available on browsers
// that support `SpeechRecognition` (e.g. Chrome/Edge); the mic button
// simply doesn't render elsewhere, and manual typing still works.

function addMicButton(textarea, container) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) return;

  const MIC_LABEL_IDLE = '開始錄音口說';
  const MIC_LABEL_ACTIVE = '停止錄音';
  const micBtn = el('button', { class: 'secondary mic-btn', html: iconHtml('mic') + MIC_LABEL_IDLE });
  let recognition = null;
  let listening = false;

  micBtn.addEventListener('click', () => {
    if (listening) {
      recognition.stop();
      return;
    }
    recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.continuous = true;
    recognition.interimResults = true;

    const baseText = textarea.value ? textarea.value.trim() + ' ' : '';
    let finalText = '';

    recognition.onresult = (event) => {
      let interim = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcriptPart = event.results[i][0].transcript;
        if (event.results[i].isFinal) finalText += transcriptPart + ' ';
        else interim += transcriptPart;
      }
      textarea.value = baseText + finalText + interim;
    };
    recognition.onerror = () => {
      listening = false;
      micBtn.innerHTML = iconHtml('mic') + MIC_LABEL_IDLE;
    };
    recognition.onend = () => {
      listening = false;
      micBtn.innerHTML = iconHtml('mic') + MIC_LABEL_IDLE;
    };

    recognition.start();
    listening = true;
    micBtn.innerHTML = iconHtml('stop') + MIC_LABEL_ACTIVE;
  });

  container.appendChild(micBtn);
}
