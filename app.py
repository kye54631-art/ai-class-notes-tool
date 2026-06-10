# ============================
# AI课堂笔记整理工具 - Flask 主入口
# ============================
import os
import sys
import json
from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
from config import Config
from database import models as db
from modules.speech_recognition import BaiduSpeechRecognizer
from modules.ai_analysis import DeepSeekAnalyzer
from modules.note_manager import create_note, update_note, list_notes, fetch_note, remove_note
from modules.export_service import ExportService
from utils.helpers import allowed_audio_file, generate_id, format_datetime, ensure_upload_dir

# 初始化 Flask
app = Flask(__name__)
app.config.from_object(Config)
app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['UPLOAD_FOLDER'] = Config.UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH

# 确保上传目录存在
ensure_upload_dir(Config.UPLOAD_FOLDER)


# ===================== 页面路由 =====================

@app.route('/')
def index():
    """首页 - 录音 / 上传"""
    return render_template('index.html')


@app.route('/editor')
@app.route('/editor/<int:note_id>')
def editor(note_id=None):
    """笔记编辑页面"""
    return render_template('editor.html', note_id=note_id)


@app.route('/history')
def history():
    """历史记录页面"""
    return render_template('history.html')


@app.route('/settings')
def settings():
    """设置页面"""
    return render_template('settings.html')


# ===================== API - 语音识别 =====================

@app.route('/api/speech/recognize', methods=['POST'])
def api_speech_recognize():
    """语音识别 API - 上传文件"""
    if 'audio' not in request.files:
        return jsonify({'success': False, 'error': '请上传音频文件'})

    file = request.files['audio']
    if file.filename == '':
        return jsonify({'success': False, 'error': '未选择文件'})

    if not allowed_audio_file(file.filename, Config.ALLOWED_AUDIO_EXTENSIONS):
        return jsonify({'success': False, 'error': f'不支持的音频格式，支持: {", ".join(Config.ALLOWED_AUDIO_EXTENSIONS)}'})

    # 保存临时文件
    ext = file.filename.rsplit('.', 1)[1].lower()
    temp_filename = f'{generate_id()}.{ext}'
    temp_path = os.path.join(Config.UPLOAD_FOLDER, temp_filename)
    file.save(temp_path)

    try:
        # 获取配置
        app_id = db.get_setting('baidu_app_id') or Config.BAIDU_SPEECH_APP_ID
        api_key = db.get_setting('baidu_api_key') or Config.BAIDU_SPEECH_API_KEY
        secret_key = db.get_setting('baidu_secret_key') or Config.BAIDU_SPEECH_SECRET_KEY

        if not all([app_id, api_key, secret_key]):
            return jsonify({
                'success': False,
                'error': '请先在设置页面配置百度语音识别API密钥。\n购买地址: https://console.bce.baidu.com/ai/#/ai/speech/overview/index'
            })

        # 执行识别
        recognizer = BaiduSpeechRecognizer(
            app_id=app_id,
            api_key=api_key,
            secret_key=secret_key
        )
        results = recognizer.recognize_file(temp_path, format=ext)

        # 合并结果
        full_text = ''.join([r for r in results])

        return jsonify({
            'success': True,
            'text': full_text,
            'segments': results
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

    finally:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.remove(temp_path)


@app.route('/api/speech/recognize-blob', methods=['POST'])
def api_speech_recognize_blob():
    """语音识别 API - 浏览器录音 blob"""
    audio_data = request.get_data()
    if not audio_data:
        return jsonify({'success': False, 'error': '无音频数据'})

    app_id = db.get_setting('baidu_app_id') or Config.BAIDU_SPEECH_APP_ID
    api_key = db.get_setting('baidu_api_key') or Config.BAIDU_SPEECH_API_KEY
    secret_key = db.get_setting('baidu_secret_key') or Config.BAIDU_SPEECH_SECRET_KEY

    if not all([app_id, api_key, secret_key]):
        return jsonify({'success': False, 'error': '请先设置百度语音识别API密钥'})

    try:
        recognizer = BaiduSpeechRecognizer(app_id, api_key, secret_key)
        results = recognizer.recognize(audio_data, format='wav', rate=16000)
        full_text = ''.join(results)
        return jsonify({'success': True, 'text': full_text, 'segments': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})# ===================== API - AI 分析 =====================

@app.route('/api/ai/analyze', methods=['POST'])
def api_ai_analyze():
    """AI 分析文本"""
    data = request.get_json()
    raw_text = data.get('text', '')
    analysis_type = data.get('type', 'full')

    if not raw_text.strip():
        return jsonify({'success': False, 'error': '请输入文本内容'})

    try:
        api_key = db.get_setting('deepseek_api_key') or Config.DEEPSEEK_API_KEY
        if not api_key:
            return jsonify({
                'success': False,
                'error': '请先在设置页面配置 DeepSeek API 密钥。\n获取地址: https://platform.deepseek.com/api_keys'
            })

        analyzer = DeepSeekAnalyzer(
            api_key=api_key,
            base_url=Config.DEEPSEEK_BASE_URL,
            model=Config.DEEPSEEK_MODEL
        )
        result = analyzer.analyze_text(raw_text, analysis_type=analysis_type)

        if 'error' in result:
            return jsonify({'success': False, 'error': result['error']})

        return jsonify({
            'success': True,
            'structured_note': result.get('structured_note', ''),
            'keywords': result.get('keywords', ''),
            'original_text': raw_text
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/ai/continue', methods=['POST'])
def api_ai_continue():
    """AI 继续分析"""
    data = request.get_json()
    raw_text = data.get('text', '')
    instruction = data.get('instruction', '')

    if not raw_text or not instruction:
        return jsonify({'success': False, 'error': '参数不完整'})

    try:
        api_key = db.get_setting('deepseek_api_key') or Config.DEEPSEEK_API_KEY
        analyzer = DeepSeekAnalyzer(
            api_key=api_key,
            base_url=Config.DEEPSEEK_BASE_URL,
            model=Config.DEEPSEEK_MODEL
        )
        result = analyzer.continue_analysis(raw_text, instruction)

        if 'error' in result:
            return jsonify({'success': False, 'error': result['error']})

        return jsonify({'success': True, 'result': result['result']})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ===================== API - 笔记管理 =====================

@app.route('/api/notes', methods=['GET'])
def api_list_notes():
    """获取笔记列表"""
    page = request.args.get('page', 1, type=int)
    keyword = request.args.get('keyword', '')
    result = list_notes(page=page, keyword=keyword)

    # 格式化时间
    for note in result['notes']:
        note['created_at_formatted'] = format_datetime(note['created_at'])
        note['updated_at_formatted'] = format_datetime(note['updated_at'])

    return jsonify({'success': True, **result})


@app.route('/api/notes/<int:note_id>', methods=['GET'])
def api_get_note(note_id):
    """获取单条笔记"""
    note = fetch_note(note_id)
    if note:
        note['created_at_formatted'] = format_datetime(note['created_at'])
        note['updated_at_formatted'] = format_datetime(note['updated_at'])
        return jsonify({'success': True, 'note': note})
    return jsonify({'success': False, 'error': '笔记不存在'}), 404


@app.route('/api/notes', methods=['POST'])
def api_create_note():
    """创建笔记"""
    data = request.get_json()
    note_id = create_note(
        title=data.get('title', '未命名笔记'),
        original_text=data.get('original_text', ''),
        structured_content=data.get('structured_content', ''),
        tags=data.get('tags', ''),
        export_format=data.get('export_format', 'word')
    )
    return jsonify({'success': True, 'note_id': note_id})


@app.route('/api/notes/<int:note_id>', methods=['PUT'])
def api_update_note(note_id):
    """更新笔记"""
    data = request.get_json()
    result = update_note(
        note_id=note_id,
        title=data.get('title', ''),
        original_text=data.get('original_text', ''),
        structured_content=data.get('structured_content', ''),
        tags=data.get('tags', ''),
        export_format=data.get('export_format', '')
    )
    if result:
        return jsonify({'success': True, 'note_id': result})
    return jsonify({'success': False, 'error': '笔记不存在'}), 404


@app.route('/api/notes/<int:note_id>', methods=['DELETE'])
def api_delete_note(note_id):
    """删除笔记"""
    success = remove_note(note_id)
    if success:
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': '笔记不存在'}), 404


# ===================== API - 导出 =====================

@app.route('/api/export/<int:note_id>/<format>', methods=['GET'])
def api_export_note(note_id, format):
    """导出笔记"""
    note = fetch_note(note_id)
    if not note:
        return jsonify({'success': False, 'error': '笔记不存在'}), 404

    try:
        content = note['structured_content'] or note['original_text']
        data, filename, mime = ExportService.export(
            title=note['title'],
            content=content,
            export_format=format
        )

        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, filename)
        with open(temp_path, 'wb') as f:
            f.write(data)

        return send_file(
            temp_path,
            mimetype=mime,
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ===================== API - 设置 =====================

@app.route('/api/settings', methods=['GET'])
def api_get_settings():
    """获取所有设置"""
    settings = db.get_all_settings()
    # 不要返回敏感信息的值，只返回是否有配置
    safe_settings = {}
    for k, v in settings.items():
        sensitive_keys = ['baidu_secret_key', 'deepseek_api_key']
        if k in sensitive_keys and v:
            safe_settings[k] = v[:4] + '****' + v[-4:] if len(v) > 8 else '*' * min(len(v), 8)
        else:
            safe_settings[k] = v
    return jsonify({'success': True, 'settings': safe_settings})


@app.route('/api/settings', methods=['POST'])
def api_save_settings():
    """保存设置"""
    data = request.get_json()
    for key, value in data.items():
        db.save_setting(key, value)
    return jsonify({'success': True})


# ===================== 错误处理 =====================

@app.errorhandler(404)
def not_found(e):
    return render_template('index.html'), 404


@app.errorhandler(413)
def too_large(e):
    return jsonify({'success': False, 'error': '文件大小超过限制(100MB)'}), 413


# ===================== 启动 =====================

if __name__ == '__main__':
    import database.models as dm
    # 初始化数据库
    dm.init_db()
    print('数据库:', dm.get_db_path(), '- 已连接')
    print('=' * 50)
    print('  AI课堂笔记整理工具  v1.0')
    print('  访问地址: http://127.0.0.1:5000')
    print('=' * 50)
    # Railway 部署时使用 PORT 环境变量，本地默认为 5000
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '127.0.0.1')
    app.run(debug=False, host=host, port=port)
