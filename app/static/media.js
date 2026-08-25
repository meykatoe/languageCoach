// TOEIC Part 1 (Photographs) items only ship a text `photoDescription` of
// the photo, not an actual image. This lazily generates (and disk-caches,
// server-side) an AI image from that description so the question looks
// like the real exam (a photo to look at) instead of describing the photo
// in words.

const PHOTO_LABEL = '顯示圖片';
const PHOTO_LOADING_LABEL = '圖片生成中...';
const PHOTO_FAILED_LABEL = '圖片生成失敗,點此重試';

function addPhotoImage(description, container) {
  const btn = el('button', { class: 'secondary photo-btn' }, PHOTO_LABEL);

  btn.addEventListener('click', async () => {
    btn.disabled = true;
    btn.textContent = PHOTO_LOADING_LABEL;
    try {
      const res = await fetch('/api/image', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        btn.textContent = `${PHOTO_FAILED_LABEL}${data.detail ? ': ' + data.detail : ''}`;
        btn.disabled = false;
        return;
      }
      const blob = await res.blob();
      const img = el('img', {
        class: 'photo-image',
        src: URL.createObjectURL(blob),
        alt: description,
      });
      btn.replaceWith(img);
    } catch (err) {
      btn.textContent = PHOTO_FAILED_LABEL;
      btn.disabled = false;
    }
  });

  container.appendChild(btn);
}
