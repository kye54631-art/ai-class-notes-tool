// ============================
// 导出功能辅助
// ============================

function quickExport(noteId, format) {
    window.open('/api/export/' + noteId + '/' + (format || 'word'), '_blank');
}
