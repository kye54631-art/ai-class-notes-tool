// ============================
// AI课堂笔记整理工具 - 主逻辑
// ============================

let currentOriginalText = '';
let currentStructuredNote = '';
let currentKeywords = '';

// ===== Tab 切换 =====
function switchTab(name) {
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));

    const tab = document.getElementById('tab-' + name);
    if (tab) tab.classList.add('active');

    // 设置对应的按钮激活状态
    const buttons = document.querySelectorAll('.tab-btn');
    const tabNames = ['record', 'upload', 'paste'];
    const idx = tabNames.indexOf(name);
    if (idx >= 0 && buttons[idx]) buttons[idx].classList.add('active');
}

// ===== 文件上传 =====
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    document.getElementById('uploadFileName').innerHTML = `
        <span style="color: var(--success);">✅ 已选择：${file.name} (${formatFileSize(file.size)})</span>
    `;
    document.getElementById('recognizeUploadBtn').disabled = false;
    document.getElementById('uploadResultCard').style.display = 'none';
    document.getElementById('analyzeUploadBtn').style.display = 'none';
}

// 拖拽上传
document.addEventListener('DOMContentLoaded', () => {
    const uploadZone = document.getElementById('uploadZone');
    if (!uploadZone) return;

    ['dragenter', 'dragover'].forEach(evt => {
        uploadZone.addEventListener(evt, e => {
            e.preventDefault();
            uploadZone.classList.add('drag-over');
        });
    });

    ['dragleave', 'drop'].forEach(evt => {
        uploadZone.addEventListener(evt, e => {
            e.preventDefault();
            uploadZone.classList.remove('drag-over');
        });
    });

    uploadZone.addEventListener('drop', e => {
        const file = e.dataTransfer.files[0];
        if (!file) return;
        document.getElementById('audioFile').files = e.dataTransfer.files;
        handleFileSelect({ target: { files: [file] } });
    });
});

// ===== 音频格式转换（浏览器端）=====
// 浏览器 AudioContext 可以原生解码 MP3/M4A/OGG/FLAC 等 → 输出 16kHz mono WAV
async function decodeAudioToWav(fileOrBlob) {
    const arrayBuf = await fileOrBlob.arrayBuffer();
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    let audioBuffer;
    try {
        audioBuffer = await audioCtx.decodeAudioData(arrayBuf);
    } finally {
        audioCtx.close();
    }

    // 重采样到 16000 Hz, mono, Int16 PCM
    const srcRate = audioBuffer.sampleRate;
    const srcData = audioBuffer.getChannelData(0);  // 只用第一声道
    const targetRate = 16000;
    const ratio = srcRate / targetRate;
    const newLength = Math.round(srcData.length / ratio);
    const pcm = new Int16Array(newLength);
    for (let i = 0; i < newLength; i++) {
        const srcIdx = i * ratio;
        const idx0 = Math.floor(srcIdx);
        const idx1 = Math.min(idx0 + 1, srcData.length - 1);
        const frac = srcIdx - idx0;
        // 线性插值
        const sample = srcData[idx0] * (1 - frac) + srcData[idx1] * frac;
        pcm[i] = Math.max(-32768, Math.min(32767, Math.round(sample * 32767)));
    }

    return encodeWAV(pcm, targetRate, 1, 16);
}

// ===== 上传识别 =====
async function recognizeUpload() {
    const fileInput = document.getElementById('audioFile');
    const file = fileInput.files[0];
    if (!file) { alert('请先选择音频文件'); return; }

    const btn = document.getElementById('recognizeUploadBtn');
    const resultBox = document.getElementById('uploadResult');
    const resultCard = document.getElementById('uploadResultCard');

    btn.disabled = true;
    btn.textContent = '⏳ 转换音频...';
    resultCard.style.display = 'block';
    resultBox.textContent = '正在解码音频，请稍候...';

    let wavBlob;
    try {
        const wavBytes = await decodeAudioToWav(file);
        wavBlob = new Blob([wavBytes], { type: 'audio/wav' });
    } catch (e) {
        // 如果浏览器解码失败（罕见），回退到原始文件上传
        wavBlob = file;
    }

    btn.textContent = '⏳ 识别中...';
    resultBox.textContent = '正在识别，请稍候...';

    const formData = new FormData();
    formData.append('audio', wavBlob, 'audio.wav');

    fetch('/api/speech/recognize', {
        method: 'POST',
        body: formData
    })
    .then(r => r.json())
    .then(data => {
        btn.disabled = false;
        btn.textContent = '🔍 开始识别';
        if (data.success) {
            resultBox.textContent = data.text;
            currentOriginalText = data.text;
            document.getElementById('analyzeUploadBtn').style.display = 'inline-flex';
            document.getElementById('analyzeUploadBtn').disabled = false;
        } else {
            resultBox.innerHTML = `<span style="color: var(--danger);">❌ ${data.error}</span>`;
        }
    })
    .catch(err => {
        btn.disabled = false;
        btn.textContent = '🔍 开始识别';
        resultBox.textContent = '网络请求出错: ' + err.message;
    });
}

// ===== 上传后分析 =====
function analyzeUpload() {
    if (!currentOriginalText) { alert('请先识别音频'); return; }
    document.getElementById('pasteText').value = currentOriginalText;
    switchTab('paste');
    analyzePastedText();
}

// ===== 粘贴文本分析 =====
function analyzePastedText() {
    const text = document.getElementById('pasteText').value.trim();
    if (!text) { alert('请输入文本内容'); return; }

    const btn = document.getElementById('analyzePasteBtn');
    const resultCard = document.getElementById('pasteResultCard');
    const resultBox = document.getElementById('pasteResult');
    const type = document.getElementById('analysisType').value;

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> AI正在分析中，请稍候...';
    resultCard.style.display = 'block';
    resultBox.innerHTML = '<p style="color: var(--text-muted); text-align: center; padding: 2rem;">🤖 DeepSeek 正在分析文本，生成结构化笔记...</p>';

    fetch('/api/ai/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text, type: type })
    })
    .then(r => r.json())
    .then(data => {
        btn.disabled = false;
        btn.innerHTML = '🤖 AI 智能分析生成笔记';
        if (data.success) {
            currentOriginalText = data.original_text || text;
            currentStructuredNote = data.structured_note || '';
            currentKeywords = data.keywords || '';

            // 渲染 Markdown 为 HTML
            resultBox.innerHTML = renderMarkdown(currentStructuredNote);

            // 显示关键词
            if (currentKeywords) {
                const kwSection = document.getElementById('keywordsSection');
                const kwTags = document.getElementById('keywordsTags');
                kwSection.style.display = 'block';
                kwTags.innerHTML = currentKeywords.split('\n')
                    .filter(k => k.trim())
                    .slice(0, 20)
                    .map(k => `<span class="keyword-tag">${escHtml(k.replace(/^[\d\.\-\s]+/, ''))}</span>`)
                    .join('');
            }
        } else {
            resultBox.innerHTML = `<span style="color: var(--danger);">❌ ${data.error}</span>`;
        }
    })
    .catch(err => {
        btn.disabled = false;
        btn.innerHTML = '🤖 AI 智能分析生成笔记';
        resultBox.innerHTML = '<span style="color: var(--danger);">网络请求出错: ' + err.message + '</span>';
    });
}

// ===== 跳转编辑器 =====
function openInEditor() {
    if (!currentStructuredNote) return;
    saveCurrentThenOpen();
}

function saveCurrentThenOpen() {
    const title = prompt('请输入笔记标题：', '新笔记');
    if (title === null) return; // 取消

    fetch('/api/notes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            title: title || '未命名笔记',
            original_text: currentOriginalText,
            structured_content: currentStructuredNote,
            tags: currentKeywords.split('\n').filter(k => k.trim()).slice(0, 5).join(','),
            export_format: 'word'
        })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            window.location.href = '/editor/' + data.note_id;
        }
    });
}

function saveAndGoHistory() {
    if (!currentStructuredNote) return;
    const title = prompt('请输入笔记标题：', '新笔记');
    if (title === null) return;

    fetch('/api/notes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            title: title || '未命名笔记',
            original_text: currentOriginalText,
            structured_content: currentStructuredNote,
            tags: currentKeywords.split('\n').filter(k => k.trim()).slice(0, 5).join(','),
            export_format: 'word'
        })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            alert('✅ 笔记已保存！');
            window.location.href = '/history';
        }
    });
}

// ===== 简单 Markdown 渲染器 =====
function renderMarkdown(md) {
    if (!md) return '';
    return md
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/^#### (.+)$/gm, '<h4>$1</h4>')
        .replace(/^### (.+)$/gm, '<h3>$1</h3>')
        .replace(/^## (.+)$/gm, '<h2>$1</h2>')
        .replace(/^# (.+)$/gm, '<h1>$1</h1>')
        .replace(/\*{2}(.+?)\*{2}/g, '<strong>$1</strong>')
        .replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>')
        .replace(/^\- (.+)$/gm, '<li>$1</li>')
        .replace(/^\d+\.\s(.+)$/gm, '<li>$1</li>')
        .replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>')
        .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
        .replace(/\n\n/g, '<br><br>')
        .replace(/\n/g, '<br>');
}

// ===== 工具函数 =====
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function escHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
