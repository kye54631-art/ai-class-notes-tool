# ============================
# 笔记管理模块
# ============================
from database.models import save_note, get_note, get_all_notes, delete_note


def create_note(title, original_text, structured_content, tags='', export_format='word'):
    """创建新笔记"""
    if not title.strip():
        title = '未命名笔记'
    return save_note(
        title=title,
        original_text=original_text,
        structured_content=structured_content,
        tags=tags,
        export_format=export_format
    )


def update_note(note_id, title='', original_text='', structured_content='', tags='', export_format=''):
    """更新笔记"""
    existing = get_note(note_id)
    if not existing:
        return None

    title = title or existing['title']
    original_text = original_text or existing['original_text']
    structured_content = structured_content or existing['structured_content']
    tags = tags or existing['tags']
    export_format = export_format or existing['export_format']

    return save_note(
        title=title,
        original_text=original_text,
        structured_content=structured_content,
        tags=tags,
        export_format=export_format,
        note_id=note_id
    )


def list_notes(page=1, keyword=''):
    """列表查询笔记"""
    return get_all_notes(page=page, keyword=keyword)


def fetch_note(note_id):
    """获取笔记详情"""
    return get_note(note_id)


def remove_note(note_id):
    """删除笔记"""
    return delete_note(note_id)
