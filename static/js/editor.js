// ============================
// 编辑器逻辑
// ============================
let currentNoteId = null;
let noteTitle = '';
let noteTags = '';
let originalText = '';

document.addEventListener('DOMContentLoaded', () => {
    // 从 URL 判断是否为编辑已有笔记
    const path = window.location.pathname;
    const match = path.match(/\/editor\/(\d+)/);
    if (match) {
        currentNoteId = parseInt(match[1]);
        loadNote(currentNoteId);
    } else {
        // 检查是否有通过 localStorage 传递的内容
        const cached = localStorage.getItem('pending_note');
        if (cached) {
            try {
                const note = JSON.parse(cached);
                document.getElementById('noteTitle').value = note.title || '未命名笔记';
                document.getElementById('editorContent').value = note.structured_content || '';
                originalText = note.original_text || '';
                noteTags = note.tags || '';
                updatePreview();
                localStorage.removeItem('pending_note');
            } catch (e) {}
        }
    }

    // 监听编辑内容变化 → 实时预览
    const editor = document.getElementById('editorContent');
    editor.addEventListener('input', updatePreview);

    // 初始预览
    updatePreview();
});

function loadNote(id) {
    fetch('/api/notes/' + id)
        .then(r => r.json())
        .then(data => {
            if (data.success && data.note) {
                const n = data.note;
                currentNoteId = n.id;
                document.getElementById('noteTitle').value = n.title;
                document.getElementById('editorContent').value = n.structured_content || n.original_text;
                originalText = n.original_text;
                noteTags = n.tags;
                updatePreview();
                showMessage('✅ 笔记已加载', 'success');
            } else {
                showMessage('❌ 笔记未找到', 'error');
            }
        })
        .catch(err => {
            showMessage('❌ 加载失败: ' + err.message, 'error');
        });
}

function updatePreview() {
    const content = document.getElementById('editorContent').value;
    const preview = document.getElementById('previewContent');
    if (content.trim()) {
        preview.innerHTML = renderMarkdown(content);
    } else {
        preview.innerHTML = '<p style="color: var(--text-muted); text-align: center; padding-top: 3rem;">开始编辑，此处将显示预览效果</p>';
    }
}

function togglePreview() {
    const editPanel = document.getElementById('editPanel');
    const previewPanel = document.getElementById('previewPanel');
    const layout = document.getElementById('editorLayout');

    if (editPanel.style.display === 'none') {
        editPanel.style.display = '';
        previewPanel.style.display = '';
        layout.classList.remove('full');
    } else {
        editPanel.style.display = 'none';
        previewPanel.style.display = '';
        layout.classList.add('full');
    }
}

function saveNote() {
    const title = document.getElementById('noteTitle').value.trim() || '未命名笔记';
    const content = document.getElementById('editorContent').value;

    const body = {
        title: title,
        structured_content: content,
        original_text: originalText,
        tags: noteTags
    };

    const method = currentNoteId ? 'PUT' : 'POST';
    const url = currentNoteId ? '/api/notes/' + currentNoteId : '/api/notes';

    fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json; charset=utf-8' },
        body: JSON.stringify(body)
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            if (!currentNoteId) currentNoteId = data.note_id;
            showMessage('✅ 笔记已保存', 'success');
            // 更新 URL
            if (window.location.pathname !== '/editor/' + currentNoteId) {
                window.history.replaceState(null, '', '/editor/' + currentNoteId);
            }
        } else {
            showMessage('❌ 保存失败: ' + data.error, 'error');
        }
    });
}

function exportNote() {
    if (!currentNoteId) {
        alert('请先保存笔记');
        return;
    }
    const format = document.getElementById('exportFormat').value;
    window.open('/api/export/' + currentNoteId + '/' + format, '_blank');
}

function continueAI() {
    const instruction = document.getElementById('aiInstruction').value.trim();
    if (!instruction) { alert('请输入AI处理指令'); return; }

    const content = document.getElementById('editorContent').value;
    const indicator = document.getElementById('loadingIndicator');
    indicator.style.display = 'block';

    // 组合原始文本和当前笔记
    const textToProcess = originalText || content;

    fetch('/api/ai/continue', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            text: textToProcess,
            instruction: instruction
        })
    })
    .then(r => r.json())
    .then(data => {
        indicator.style.display = 'none';
        if (data.success) {
            document.getElementById('editorContent').value = data.result;
            updatePreview();
            showMessage('✅ AI处理完成', 'success');
        } else {
            showMessage('❌ ' + data.error, 'error');
        }
    })
    .catch(err => {
        indicator.style.display = 'none';
        showMessage('❌ 请求失败: ' + err.message, 'error');
    });
}

function showMessage(msg, type) {
    const area = document.getElementById('messageArea');
    area.innerHTML = `<div class="alert alert-${type}">${msg}</div>`;
    setTimeout(() => area.innerHTML = '', 3000);
}

// 共享 Markdown 渲染器（来自 main.js）
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
