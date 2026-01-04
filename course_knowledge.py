"""
课程知识点管理模块
支持MD文件读写和LLM生成知识点
"""
import re
from pathlib import Path
from typing import List, Dict, Optional
import config
from llm_service import LLMService
import prompts


class CourseKnowledge:
    """课程知识点管理类"""
    
    def __init__(self):
        """初始化课程知识点管理器"""
        self.llm_service = LLMService()
        self.courses_dir = Path(config.COURSES_DIR)
        self.courses_dir.mkdir(parents=True, exist_ok=True)
    
    def get_course_file_path(self, course_name: str) -> Path:
        """
        获取课程知识点文件路径
        
        Args:
            course_name: 课程名称
        
        Returns:
            文件路径
        """
        filename = f"{course_name}课程知识点.md"
        return self.courses_dir / filename
    
    def course_exists(self, course_name: str) -> bool:
        """
        检查课程知识点文件是否存在
        
        Args:
            course_name: 课程名称
        
        Returns:
            是否存在
        """
        file_path = self.get_course_file_path(course_name)
        return file_path.exists()
    
    def load_knowledge_points(self, course_name: str) -> Dict:
        """
        从MD文件加载知识点
        
        Args:
            course_name: 课程名称
        
        Returns:
            包含课程信息和知识点列表的字典
        """
        file_path = self.get_course_file_path(course_name)
        
        if not file_path.exists():
            raise FileNotFoundError(f"课程知识点文件不存在: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析MD文件
        result = {
            'course_name': course_name,
            'course_description': '',
            'knowledge_points': []
        }
        
        # 提取课程名称（从#标题）
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            result['course_name'] = title_match.group(1).strip()
        
        # 提取课程描述
        desc_match = re.search(r'##\s+课程描述\s*\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
        if desc_match:
            result['course_description'] = desc_match.group(1).strip()
        
        # 提取知识点列表
        points_match = re.search(r'##\s+知识点列表\s*\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
        if points_match:
            points_text = points_match.group(1)
            # 解析每个知识点（支持多种格式）
            # 格式1: 1. 知识点名称：描述
            # 格式2: - 知识点名称：描述
            # 格式3: 1. 知识点名称
            point_pattern = r'(?:^\d+\.|^[-*])\s*(.+?)(?:\n|$)'
            matches = re.finditer(point_pattern, points_text, re.MULTILINE)
            
            for match in matches:
                point_text = match.group(1).strip()
                # 分离名称和描述
                if '：' in point_text or ':' in point_text:
                    parts = re.split(r'[：:]', point_text, 1)
                    name = parts[0].strip()
                    desc = parts[1].strip() if len(parts) > 1 else ''
                else:
                    name = point_text
                    desc = ''
                
                result['knowledge_points'].append({
                    'name': name,
                    'description': desc
                })
        
        return result
    
    def generate_knowledge_points(self, learning_goal: str, course_name: str = None) -> Dict:
        """
        使用LLM生成知识点
        
        Args:
            learning_goal: 学习目标
            course_name: 课程名称（可选，如果不提供则从学习目标推断）
        
        Returns:
            包含课程信息和知识点列表的字典
        """
        # 如果没有提供课程名称，使用学习目标作为课程名称
        if not course_name:
            course_name = learning_goal
        
        # 生成提示词
        prompt = prompts.get_knowledge_points_extraction_prompt(learning_goal, course_name)
        
        # 调用LLM
        messages = [
            {'role': 'user', 'content': prompt}
        ]
        
        result = self.llm_service.chat_json(messages, stream=True)
        
        # 确保返回格式正确
        if 'knowledge_points' not in result:
            raise ValueError("LLM返回的数据格式不正确，缺少'knowledge_points'字段")
        
        return result
    
    def save_knowledge_points(self, course_data: Dict):
        """
        保存知识点到MD文件
        
        Args:
            course_data: 课程数据字典，包含course_name, course_description, knowledge_points
        """
        course_name = course_data.get('course_name', '')
        if not course_name:
            raise ValueError("课程名称不能为空")
        
        file_path = self.get_course_file_path(course_name)
        
        # 构建MD内容
        md_content = f"# {course_name}\n\n"
        
        course_description = course_data.get('course_description', '')
        if course_description:
            md_content += f"## 课程描述\n\n{course_description}\n\n"
        
        md_content += "## 知识点列表\n\n"
        
        knowledge_points = course_data.get('knowledge_points', [])
        for i, point in enumerate(knowledge_points, 1):
            name = point.get('name', '')
            desc = point.get('description', '')
            if desc:
                md_content += f"{i}. {name}：{desc}\n"
            else:
                md_content += f"{i}. {name}\n"
        
        # 保存文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
    
    def get_or_generate_knowledge_points(self, learning_goal: str, course_name: str = None) -> Dict:
        """
        获取或生成知识点（如果文件存在则读取，否则生成并保存）
        
        Args:
            learning_goal: 学习目标
            course_name: 课程名称（可选）
        
        Returns:
            包含课程信息和知识点列表的字典
        """
        # 如果没有提供课程名称，使用学习目标作为课程名称
        if not course_name:
            course_name = learning_goal
        
        # 检查文件是否存在
        if self.course_exists(course_name):
            # 读取现有文件
            return self.load_knowledge_points(course_name)
        else:
            # 生成新知识点
            course_data = self.generate_knowledge_points(learning_goal, course_name)
            # 保存到文件
            self.save_knowledge_points(course_data)
            return course_data
