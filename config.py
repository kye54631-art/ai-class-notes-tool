# ============================
# AI课堂笔记整理工具 - 配置文件
# ============================
import os

class Config:
    """应用配置"""
    # Flask 配置
    SECRET_KEY = os.environ.get('SECRET_KEY', 'ai-classroom-notes-secret-key-2024')

    # 数据库配置 - SQLite
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DATABASE_PATH = os.path.join(BASE_DIR, 'database', 'notes.db')

    # 文件上传配置
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 最大上传100MB
    ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'm4a', 'flac', 'aac', 'ogg', 'wma', 'pcm', 'amr'}

    # 百度语音识别 API 配置
    BAIDU_SPEECH_APP_ID = os.environ.get('BAIDU_SPEECH_APP_ID', '')
    BAIDU_SPEECH_API_KEY = os.environ.get('BAIDU_SPEECH_API_KEY', '')
    BAIDU_SPEECH_SECRET_KEY = os.environ.get('BAIDU_SPEECH_SECRET_KEY', '')

    # DeepSeek API 配置
    DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
    DEEPSEEK_BASE_URL = os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
    DEEPSEEK_MODEL = os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat')

    # 默认设置
    DEFAULT_EXPORT_FORMAT = 'word'  # txt / word / pdf
    DEFAULT_LANGUAGE = 'zh-CN'
