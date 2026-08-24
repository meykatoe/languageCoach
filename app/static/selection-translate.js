// Site-wide "selection translation": select any text on the page and it is
// replaced in place with its Traditional Chinese translation (hover to see
// the original text again via the title attribute). If the selection is a
// single word, the backend also auto-saves it into the vocabulary book
// (/vocab), shown here with a dotted underline.
(function () {
  let debounceTimer = null;

  function rangeContainsInteractive(range) {
    const frag = range.cloneContents();
    return !!frag.querySelector('input, button, select, textarea, a, .translated-text');
  }

  async function replaceSelectionWithTranslation(range, text) {
    const span = document.createElement('span');
    span.className = 'translated-text translated-pending';
    span.textContent = text;

    try {
      range.deleteContents();
      range.insertNode(span);
    } catch (err) {
      return; // selection no longer maps to a valid, single range
    }

    try {
      const res = await fetch('/api/translate/text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });
      const data = await res.json().catch(() => ({}));
      if (!span.isConnected) return; // page changed underneath us
      span.classList.remove('translated-pending');
      if (res.ok) {
        span.textContent = data.translation;
        span.title = data.added_to_vocab ? `${text}\n(已加入單字本)` : text;
        if (data.added_to_vocab) span.classList.add('translated-text-vocab');
      } else {
        span.textContent = text; // revert on failure
      }
    } catch (err) {
      if (span.isConnected) {
        span.classList.remove('translated-pending');
        span.textContent = text;
      }
    }
  }

  function handleSelection() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      const selection = window.getSelection();
      if (!selection || selection.isCollapsed || !selection.rangeCount) return;

      const text = selection.toString().trim();
      if (!text || text.length > 400) return;

      const anchorNode = selection.anchorNode;
      const anchorEl = anchorNode && (anchorNode.nodeType === 1 ? anchorNode : anchorNode.parentElement);
      if (anchorEl && anchorEl.closest('input, textarea, .translated-text')) return;

      const range = selection.getRangeAt(0).cloneRange();
      if (rangeContainsInteractive(range)) return;

      selection.removeAllRanges();
      replaceSelectionWithTranslation(range, text);
    }, 300);
  }

  document.addEventListener('mouseup', handleSelection);
  document.addEventListener('touchend', handleSelection);
  document.addEventListener('keyup', (e) => {
    if (e.shiftKey || e.key.startsWith('Arrow')) handleSelection();
  });
})();
