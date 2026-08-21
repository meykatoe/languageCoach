const statusLine = document.getElementById('status-line');
const apiKeyInput = document.getElementById('api-key-input');
const modelSelect = document.getElementById('model-select');
const modelCustomInput = document.getElementById('model-custom-input');
const saveBtn = document.getElementById('save-btn');
const testBtn = document.getElementById('test-btn');
const clearBtn = document.getElementById('clear-btn');
const saveStatus = document.getElementById('save-status');
const testStatus = document.getElementById('test-status');

const KNOWN_MODELS = ['gpt-4o-mini', 'gpt-4o', 'gpt-4.1-mini', 'gpt-4.1'];

const testBtnIcon = document.getElementById('test-btn-icon');
if (testBtnIcon && typeof iconHtml === 'function') testBtnIcon.innerHTML = iconHtml('bolt');

function applySettings(data) {
  if (data.has_api_key) {
    const sourceLabel = data.api_key_source === 'database' ? '此設定頁' : '後端 .env 環境變數';
    statusLine.textContent = `目前已設定 API Key(來源: ${sourceLabel}${data.api_key_hint ? '，結尾 ' + data.api_key_hint : ''})，使用模型: ${data.openai_model}`;
  } else {
    statusLine.textContent = '尚未設定 API Key，寫作/口說 AI 評分與 AI 出題功能無法使用。';
  }

  if (KNOWN_MODELS.includes(data.openai_model)) {
    modelSelect.value = data.openai_model;
    modelCustomInput.style.display = 'none';
  } else {
    modelSelect.value = '__custom__';
    modelCustomInput.style.display = 'block';
    modelCustomInput.value = data.openai_model;
  }
}

fetch('/api/settings').then(r => r.json()).then(applySettings);

modelSelect.addEventListener('change', () => {
  modelCustomInput.style.display = modelSelect.value === '__custom__' ? 'block' : 'none';
});

saveBtn.addEventListener('click', async () => {
  const model = modelSelect.value === '__custom__' ? modelCustomInput.value.trim() : modelSelect.value;
  const body = { openai_model: model || null };
  if (apiKeyInput.value.trim()) {
    body.openai_api_key = apiKeyInput.value.trim();
  }
  saveBtn.disabled = true;
  saveStatus.textContent = '儲存中...';
  try {
    const res = await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) {
      saveStatus.textContent = `儲存失敗: ${data.detail || res.status}`;
      return;
    }
    apiKeyInput.value = '';
    saveStatus.textContent = '已儲存。';
    applySettings(data);
  } finally {
    saveBtn.disabled = false;
  }
});

testBtn.addEventListener('click', async () => {
  testBtn.disabled = true;
  const typedKey = apiKeyInput.value.trim();
  testStatus.textContent = typedKey
    ? '測試輸入框中的 Key...'
    : '測試目前已儲存的 Key...';
  try {
    const res = await fetch('/api/settings/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ openai_api_key: typedKey || null }),
    });
    const data = await res.json();
    testStatus.textContent = data.message;
    testStatus.className = data.ok ? 'result-correct' : 'result-wrong';
  } catch (e) {
    testStatus.textContent = '測試請求失敗,請確認伺服器是否正常運作。';
    testStatus.className = 'result-wrong';
  } finally {
    testBtn.disabled = false;
  }
});

clearBtn.addEventListener('click', async () => {
  clearBtn.disabled = true;
  try {
    const res = await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ clear_api_key: true }),
    });
    const data = await res.json();
    saveStatus.textContent = '已清除此設定頁儲存的 API Key(若後端 .env 有設定則會改用該組)。';
    applySettings(data);
  } finally {
    clearBtn.disabled = false;
  }
});
