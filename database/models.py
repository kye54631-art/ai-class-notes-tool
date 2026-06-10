# ============================
# 数据库模型
# ============================
import sqlite3
import os
from datetime import datetime


import sys
# 确保 working dir 正确
import os as _os
_pkg_dir = _os.path.dirname(_os.path.abspath(__file__))
_proj_dir = _os.path.dirname(_pkg_dir)
if _proj_dir not in sys.path:
    sys.path.insert(0, _proj_dir)


def get_db_path():
    """获取数据库路径"""
    import os
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    return os.path.join(base_dir, 'database', 'notes.db')


def init_db():
    """初始化数据库，创建表"""
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()

    # 笔记表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL DEFAULT '未命名笔记',
            original_text TEXT DEFAULT '',
            structured_content TEXT DEFAULT '',
            tags TEXT DEFAULT '',
            export_format TEXT DEFAULT 'word',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 设置表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT DEFAULT ''
        )
    ''')

    # 插入默认设置
    default_settings = [
        ('default_export_format', 'word'),
        ('language', 'zh-CN'),
        ('baidu_app_id', ''),
        ('baidu_api_key', ''),
        ('baidu_secret_key', ''),
        ('deepseek_api_key', ''),
    ]
    for key, value in default_settings:
        cursor.execute(
            'INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)',
            (key, value)
        )

    conn.commit()
    conn.close()
    return True


def get_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def save_note(title, original_text, structured_content, tags='', export_format='word', note_id=None):
    """保存或更新笔记"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if note_id:
        cursor.execute('''
            UPDATE notes SET title=?, original_text=?, structured_content=?,
            tags=?, export_format=?, updated_at=?
            WHERE id=?
        ''', (title, original_text, structured_content, tags, export_format, now, note_id))
    else:
        cursor.execute('''
            INSERT INTO notes (title, original_text, structured_content, tags, export_format, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (title, original_text, structured_content, tags, export_format, now, now))
        note_id = cursor.lastrowid

    conn.commit()
    conn.close()
    return note_id


def get_note(note_id):
    """获取单条笔记"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM notes WHERE id=?', (note_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_notes(page=1, per_page=20, keyword=''):
    """获取所有笔记（分页+搜索）"""
    conn = get_connection()
    cursor = conn.cursor()
    offset = (page - 1) * per_page

    if keyword:
        cursor.execute(
            'SELECT * FROM notes WHERE title LIKE ? OR tags LIKE ? ORDER BY updated_at DESC LIMIT ? OFFSET ?',
            (f'%{keyword}%', f'%{keyword}%', per_page, offset)
        )
        rows = cursor.fetchall()
        cursor.execute(
            'SELECT COUNT(*) FROM notes WHERE title LIKE ? OR tags LIKE ?',
            (f'%{keyword}%', f'%{keyword}%')
        )
        total = cursor.fetchone()[0]
    else:
        cursor.execute('SELECT COUNT(*) FROM notes')
        total = cursor.fetchone()[0]
        cursor.execute('SELECT * FROM notes ORDER BY updated_at DESC LIMIT ? OFFSET ?', (per_page, offset))
        rows = cursor.fetchall()
    conn.close()

    return {
        'notes': [dict(r) for r in rows],
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page if total > 0 else 1
    }


def delete_note(note_id):
    """删除笔记"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM notes WHERE id=?', (note_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def get_setting(key):
    """获取设置值"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM settings WHERE key=?', (key,))
    row = cursor.fetchone()
    conn.close()
    return row['value'] if row else ''


def save_setting(key, value):
    """保存设置值"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=?',
        (key, value, value)
    )
    conn.commit()
    conn.close()
    return True


def get_all_settings():
    """获取所有设置"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM settings')
    rows = cursor.fetchall()
    conn.close()
    return {row['key']: row['value'] for row in rows}
