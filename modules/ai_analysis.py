# ============================
# DeepSeek AI 分析模块
# ============================
from openai import OpenAI


class DeepSeekAnalyzer:
    """使用 DeepSeek API 进行课堂笔记智能分析"""

    def __init__(self, api_key='', base_url='https://api.deepseek.com', model='deepseek-chat'):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.client = None
        if api_key:
            self._init_client()

    def _init_client(self):
        """初始化 OpenAI 兼容客户端"""
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    def analyze_text(self, raw_text, analysis_type='full'):
        """
        分析文本，生成结构化笔记

        参数:
            raw_text: str - 课堂录制的原始文本
            analysis_type: str - 分析类型
                'full' - 全面分析（默认）
                'summary' - 仅摘要
                'keypoints' - 仅要点提取
                'outline' - 仅大纲
        返回:
            dict - {structured_note, keywords, summary, outline}
        """
        if not self.client:
            return {'error': '请先配置 DeepSeek API 密钥'}

        prompts = self._get_prompts(raw_text, analysis_type)

        result = {}
        try:
            # 生成结构化笔记（主要任务）
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': self._get_system_prompt()},
                    {'role': 'user', 'content': prompts['main']}
                ],
                temperature=0.3,
                max_tokens=4096,
                top_p=0.9
            )
            result['structured_note'] = resp.choices[0].message.content.strip()

            # 提取关键词
            if analysis_type == 'full':
                resp_kw = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {'role': 'user', 'content': prompts['keywords']}
                    ],
                    temperature=0.1,
                    max_tokens=512
                )
                result['keywords'] = resp_kw.choices[0].message.content.strip()

        except Exception as e:
            result['error'] = f'AI分析出错: {str(e)}'

        return result

    def continue_analysis(self, raw_text, user_instruction):
        """
        根据用户指令继续分析/修改笔记
        """
        if not self.client:
            return {'error': '请先配置 DeepSeek API 密钥'}

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': self._get_system_prompt()},
                    {'role': 'user', 'content': f'以下是课堂内容原文：\n\n{raw_text[:3000]}\n\n根据用户要求操作: {user_instruction}'}
                ],
                temperature=0.3,
                max_tokens=4096
            )
            return {'result': resp.choices[0].message.content.strip()}
        except Exception as e:
            return {'error': f'AI分析出错: {str(e)}'}

    def _get_system_prompt(self):
        """获取系统提示词"""
        return '''你是一个专业的课堂笔记整理助手，擅长从课堂录音转录文本中提取知识点并生成结构化笔记。

请遵循以下规则：
1. 使用中文输出
2. 按层级结构组织内容（大标题 → 小标题 → 要点）
3. 标记重点内容（用 **加粗** 标记关键概念和定义）
4. 识别并归纳知识体系，不要简单罗列原文
5. 对于公式、日期、名词等需要准确无误
6. 输出格式使用 Markdown
7. 如果内容涉及多学科交叉，请分类整理
8. 最后附上本节课的知识脉络总结'''

    def _get_prompts(self, raw_text, analysis_type):
        """根据分析类型构建提示词"""
        base = raw_text[:8000]  # 限制长度

        prompts = {
            'keywords': f'从以下课堂内容中提取15-20个最重要的关键词或术语，按重要性排序，每行一个：\n\n{base}',
        }

        if analysis_type == 'full':
            prompts['main'] = f'''请将以下课堂录音转录文本整理为一份结构清晰的课堂笔记：

文本内容：
{base}

要求：
1. 先用一个##标题概括本节课程主题
2. 用"📌 本节概述"开头写一段100字以内的总结
3. 按知识体系整理成大标题、小标题的层级结构
4. 每个知识点下列出关键要点
5. 用 **加粗** 突出重要概念
6. 最后用"🔑 关键知识脉络"总结本节逻辑主线
7. 输出为Markdown格式'''
        elif analysis_type == 'summary':
            prompts['main'] = f'请对以下课堂内容进行摘要总结，控制在200字以内：\n\n{base}'
        elif analysis_type == 'keypoints':
            prompts['main'] = f'请提取以下课堂内容的核心要点，分条列出：\n\n{base}'
        elif analysis_type == 'outline':
            prompts['main'] = f'请为以下课堂内容生成一个层级大纲：\n\n{base}'

        return prompts
