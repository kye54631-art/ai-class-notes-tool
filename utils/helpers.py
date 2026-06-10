# ============================
# 工具函数
# ============================
import os
import uuid
from datetime import datetime


def generate_id():
    """生成唯一ID"""
    return uuid.uuid4().hex[:12]


def allowed_audio_file(filename, allowed_extensions):
    """检查音频文件扩展名是否允许"""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in allowed_extensions


def format_datetime(dt_str):
    """格式化时间字符串"""
    try:
        dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
        now = datetime.now()
        diff = now - dt

        if diff.days == 0:
            if diff.seconds < 60:
                return '刚刚'
            elif diff.seconds < 3600:
                return f'{diff.seconds // 60}分钟前'
            else:
                return f'{diff.seconds // 3600}小时前'
        elif diff.days == 1:
            return '昨天'
        elif diff.days < 7:
            return f'{diff.days}天前'
        else:
            return dt.strftime('%Y-%m-%d %H:%M')
    except Exception:
        return dt_str


def ensure_upload_dir(upload_folder):
    """确保上传目录存在"""
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    return True


def clean_html(text):
    """简单的HTML清除"""
    import re
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)
