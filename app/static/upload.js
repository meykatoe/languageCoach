// Upload page: send a PDF/DOCX/TXT file to /api/upload, then render the
// AI-generated practice items using app.js's shared renderQuiz().

const uploadFileInput = document.getElementById('upload-file');
const uploadExamInput = document.getElementById('upload-exam');
const uploadCountInput = document.getElementById('upload-count');
const uploadBtn = document.getElementById('upload-btn');
const uploadStatus = document.getElementById('upload-status');

const uploadBtnIcon = document.getElementById('upload-btn-icon');
if (uploadBtnIcon && typeof iconHtml === 'function') uploadBtnIcon.innerHTML = iconHtml('sparkle');

uploadBtn.addEventListener('click', async () => {
  const file = uploadFileInput.files[0];
  if (!file) {
    uploadStatus.textContent = '請先選擇要上傳的檔案。';
    uploadStatus.className = 'result-wrong';
    return;
  }

  const count = parseInt(uploadCountInput.value, 10) || 3;
  const formData = new FormData();
  formData.append('file', file);
  formData.append('count', String(count));
  if (uploadExamInput.value.trim()) {
    formData.append('exam', uploadExamInput.value.trim());
  }

  uploadBtn.disabled = true;
  uploadStatus.textContent = 'AI 分析檔案並出題中,請稍候...';
  uploadStatus.className = 'question-meta';
  try {
    const res = await fetch('/api/upload', { method: 'POST', body: formData });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      uploadStatus.textContent = `出題失敗: ${data.detail || res.status}`;
      uploadStatus.className = 'result-wrong';
      return;
    }
    uploadStatus.textContent = `已產生 ${data.length} 題,顯示於下方,答對答錯一樣會計入學習紀錄。`;
    uploadStatus.className = 'result-correct';
    renderQuiz(data);
  } catch (e) {
    uploadStatus.textContent = '上傳請求失敗,請確認伺服器是否正常運作。';
    uploadStatus.className = 'result-wrong';
  } finally {
    uploadBtn.disabled = false;
  }
});
