# ============================
# 百度语音识别模块
# ============================
import base64
import io
import json
import os
import subprocess
import tempfile
import time
import requests

# 百度 dev_pid=1537 支持的音频格式
BAIDU_SUPPORTED_FORMATS = {'pcm', 'wav', 'amr', 'm4a'}

# ffmpeg 常见路径
_FFMPEG_PATHS = [
    os.environ.get('FFMPEG_PATH', ''),
    'ffmpeg',
    'ffmpeg.exe',
    r'C:\ffmpeg\bin\ffmpeg.exe',
    r'C:\Program Files\ffmpeg\bin\ffmpeg.exe',
    r'C:\Program Files\SteelSeries\GG\apps\moments\ffmpeg.exe',
]

_FFMPEG_EXE = None


def _get_ffmpeg():
    """定位 ffmpeg 可执行文件"""
    global _FFMPEG_EXE
    if _FFMPEG_EXE is not None:
        return _FFMPEG_EXE
    for p in _FFMPEG_PATHS:
        if not p:
            continue
        if p == 'ffmpeg' or p == 'ffmpeg.exe':
            try:
                subprocess.run([p, '-version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
                _FFMPEG_EXE = p
                return _FFMPEG_EXE
            except Exception:
                continue
        elif os.path.exists(p):
            _FFMPEG_EXE = p
            return _FFMPEG_EXE
    return None


def _convert_to_wav(file_path):
    """使用 ffmpeg 将任意音频文件转换为 WAV（16kHz mono）"""
    ffmpeg = _get_ffmpeg()
    if not ffmpeg:
        raise Exception(
            '需要 ffmpeg 来识别此音频格式。\n'
            '请下载 ffmpeg 放入 C:\\ffmpeg\\bin\\ 或设置环境变量 FFMPEG_PATH'
        )

    wav_path = file_path + '.wav'
    try:
        subprocess.run([
            ffmpeg, '-y', '-i', file_path,
            '-acodec', 'pcm_s16le', '-ac', '1', '-ar', '16000',
            wav_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60, check=True)

        with open(wav_path, 'rb') as f:
            return f.read()
    except subprocess.CalledProcessError as e:
        raise Exception(f'ffmpeg 转换失败: {e}')
    except FileNotFoundError:
        raise Exception(f'未找到 ffmpeg: {ffmpeg}')
    finally:
        if os.path.exists(wav_path):
            os.unlink(wav_path)


class BaiduSpeechRecognizer:
    """百度语音识别 - 短语音识别（<60秒）"""

    BASE_URL = 'https://vop.baidu.com/server_api'

    def __init__(self, app_id='', api_key='', secret_key=''):
        self.app_id = app_id
        self.api_key = api_key
        self.secret_key = secret_key
        self.access_token = None
        self.token_expire_time = 0

    def _get_access_token(self):
        """获取百度 access_token"""
        if self.access_token and time.time() < self.token_expire_time - 3600:
            return self.access_token

        url = 'https://aip.baidubce.com/oauth/2.0/token'
        params = {
            'grant_type': 'client_credentials',
            'client_id': self.api_key,
            'client_secret': self.secret_key
        }
        resp = requests.post(url, params=params, timeout=10)
        result = resp.json()

        if 'access_token' in result:
            self.access_token = result['access_token']
            self.token_expire_time = time.time() + result.get('expires_in', 2592000)
            return self.access_token
        else:
            raise Exception(f'获取百度Token失败: {result}')

    def recognize(self, audio_data, format='pcm', rate=16000):
        """
        识别短语音（<60秒）

        参数:
            audio_data: bytes - 音频数据
            format: str - 文件格式 (pcm/wav/mp3/m4a/amr 等)
            rate: int - 采样率 (8000/16000)
        返回:
            list - 识别结果

        内部自动处理: 不支持的格式 → WAV转换 → PCM剥离
        """
        token = self._get_access_token()

        # 如果格式不被直接支持，先转为 WAV
        if format.lower() not in BAIDU_SUPPORTED_FORMATS:
            tmp_path = None
            try:
                # 写入临时文件供 ffmpeg 处理
                suffix = f'.{format.lower()}' if format else '.audio'
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_in:
                    tmp_in.write(audio_data)
                    tmp_path = tmp_in.name
                audio_data = _convert_to_wav(tmp_path)
                format = 'wav'
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        # WAV → 剥离头，提取裸PCM
        if format == 'wav' and len(audio_data) > 44:
            if audio_data[:4] == b'RIFF':
                idx = audio_data.find(b'data')
                if idx > 0:
                    audio_data = audio_data[idx + 8:]
                    format = 'pcm'

        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        audio_len = len(audio_data)

        data = {
            'format': format,
            'rate': rate,
            'channel': 1,
            'cuid': self.app_id,
            'token': token,
            'speech': audio_base64,
            'len': audio_len,
            'dev_pid': 1537
        }

        resp = requests.post(
            self.BASE_URL,
            json=data,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        result = resp.json()

        if result.get('err_no') == 0:
            return result.get('result', [])
        else:
            error_msg = result.get('err_msg', '未知错误')
            raise Exception(f'语音识别失败 [{result.get("err_no")}]: {error_msg}')

    def recognize_file(self, file_path, format=None):
        """识别音频文件"""
        # 自动检测格式
        if format is None:
            ext = file_path.rsplit('.', 1)[-1].lower() if '.' in file_path else 'wav'
            format = ext

        with open(file_path, 'rb') as f:
            audio_data = f.read()

        return self.recognize(audio_data, format=format)

    def recognize_long_audio(self, file_path, format='wav', rate=16000, callback_url=''):
        """
        长语音识别（>60秒）- 使用极速版长语音API
        需要提交音频到服务器，服务器识别后推送结果到回调地址
        """
        token = self._get_access_token()

        # 读取音频文件
        with open(file_path, 'rb') as f:
            audio_data = f.read()
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        audio_len = len(audio_data)

        data = {
            'format': format,
            'rate': rate,
            'channel': 1,
            'cuid': self.app_id,
            'token': token,
            'speech': audio_base64,
            'len': audio_len,
            'dev_pid': 1737,  # 普通话极速版
            'callback': callback_url if callback_url else None
        }

        resp = requests.post(
            'https://vop.baidu.com/pro_api',
            json=data,
            headers={'Content-Type': 'application/json'},
            timeout=120
        )
        return resp.json()
