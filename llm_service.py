"""
LLM服务封装模块
支持ModelScope API调用和流式响应处理
"""
import json
import time
from typing import List, Dict, Optional, Iterator
from openai import OpenAI
import config


class LLMService:
    """LLM服务封装类"""
    
    def __init__(self):
        """初始化LLM服务"""
        if config.MODELSCOPE_API_KEY == 'YOUR_API_KEY_HERE':
            raise ValueError("请在config.py中配置您的ModelScope API密钥")
        
        self.client = OpenAI(
            base_url=config.MODELSCOPE_BASE_URL,
            api_key=config.MODELSCOPE_API_KEY,
        )
        self.model = config.MODELSCOPE_MODEL
        self.max_retries = 3
        self.retry_delay = 1  # 秒
    
    def _call_api(self, messages: List[Dict], stream: bool = True, **kwargs) -> Iterator[str]:
        """
        调用ModelScope API
        
        Args:
            messages: 消息列表
            stream: 是否使用流式响应
            **kwargs: 其他参数
        
        Yields:
            响应内容片段
        """
        extra_body = {
            "enable_thinking": True
        }
        
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    stream=stream,
                    extra_body=extra_body,
                    **kwargs
                )
                
                if stream:
                    done_thinking = False
                    for chunk in response:
                        if chunk.choices:
                            thinking_chunk = chunk.choices[0].delta.reasoning_content
                            answer_chunk = chunk.choices[0].delta.content
                            
                            if thinking_chunk:
                                # 思考过程可以记录，这里暂时忽略
                                pass
                            elif answer_chunk:
                                if not done_thinking:
                                    done_thinking = True
                                yield answer_chunk
                else:
                    # 非流式响应
                    content = response.choices[0].message.content
                    yield content
                
                return  # 成功则返回
                
            except Exception as e:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                else:
                    raise Exception(f"API调用失败，已重试{self.max_retries}次: {str(e)}")
    
    def chat(self, messages: List[Dict], stream: bool = True) -> str:
        """
        发送聊天消息并获取完整响应
        
        Args:
            messages: 消息列表
            stream: 是否使用流式响应
        
        Returns:
            完整的响应文本
        """
        response_parts = []
        for chunk in self._call_api(messages, stream=stream):
            response_parts.append(chunk)
        
        return ''.join(response_parts)
    
    def chat_json(self, messages: List[Dict], stream: bool = True) -> Dict:
        """
        发送聊天消息并解析JSON响应
        
        Args:
            messages: 消息列表
            stream: 是否使用流式响应
        
        Returns:
            解析后的JSON字典
        """
        response_text = self.chat(messages, stream=stream)
        
        # 尝试提取JSON（可能包含markdown代码块）
        response_text = response_text.strip()
        if response_text.startswith('```'):
            # 提取代码块中的内容
            lines = response_text.split('\n')
            json_start = False
            json_lines = []
            for line in lines:
                if line.strip().startswith('```'):
                    if json_start:
                        break
                    json_start = True
                    continue
                if json_start:
                    json_lines.append(line)
            response_text = '\n'.join(json_lines)
        
        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            raise ValueError(f"无法解析JSON响应: {str(e)}\n响应内容: {response_text}")
    
    def chat_multiple_times(self, messages: List[Dict], times: int = 3) -> List[str]:
        """
        多次调用API并返回所有结果（用于排序稳定性）
        
        Args:
            messages: 消息列表
            times: 调用次数
        
        Returns:
            多次调用的结果列表
        """
        results = []
        for i in range(times):
            result = self.chat(messages, stream=True)
            results.append(result)
            # 避免请求过快
            if i < times - 1:
                time.sleep(0.5)
        return results
