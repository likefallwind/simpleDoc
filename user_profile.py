"""
用户画像解析模块
支持YAML格式解析和验证
从课程知识点文档中提取已掌握的知识点
"""
import yaml
from typing import Dict, List, Optional
from pathlib import Path
from course_knowledge import CourseKnowledge


class UserProfile:
    """用户画像类"""
    
    def __init__(self, profile_data: Dict, load_knowledge_points: bool = True):
        """
        初始化用户画像
        
        Args:
            profile_data: 画像数据字典
            load_knowledge_points: 是否从课程文档中加载知识点（默认True）
        """
        self._validate(profile_data)
        self.data = profile_data
        self.user = profile_data.get('user', {})
        self.name = self.user.get('name', '')
        self.background = self.user.get('background', {})
        self.courses = self.background.get('courses', [])
        self.learning_goal = self.user.get('learning_goal', '')
        
        # 从课程知识点文档中提取已掌握的知识点
        self.knowledge_points = []
        if load_knowledge_points:
            self._load_knowledge_points_from_courses()
    
    @staticmethod
    def _validate(profile_data: Dict):
        """
        验证画像数据格式
        
        Args:
            profile_data: 画像数据字典
        
        Raises:
            ValueError: 如果数据格式不正确
        """
        if not isinstance(profile_data, dict):
            raise ValueError("画像数据必须是字典格式")
        
        if 'user' not in profile_data:
            raise ValueError("画像数据中缺少'user'字段")
        
        user = profile_data['user']
        if not isinstance(user, dict):
            raise ValueError("'user'字段必须是字典格式")
        
        if 'learning_goal' not in user:
            raise ValueError("用户画像中缺少'learning_goal'字段（学习目标）")
        
        if 'background' in user:
            background = user['background']
            if not isinstance(background, dict):
                raise ValueError("'background'字段必须是字典格式")
            
            if 'courses' in background:
                if not isinstance(background['courses'], list):
                    raise ValueError("'courses'字段必须是列表格式")
            
            # knowledge_points字段现在是可选的，会从课程文档中自动提取
            if 'knowledge_points' in background:
                if not isinstance(background['knowledge_points'], list):
                    raise ValueError("'knowledge_points'字段必须是列表格式")
    
    def get_background_dict(self) -> Dict:
        """
        获取背景信息字典（用于传递给LLM）
        
        Returns:
            背景信息字典
        """
        return {
            'courses': self.courses,
            'knowledge_points': self.knowledge_points
        }
    
    def has_knowledge_point(self, point_name: str) -> bool:
        """
        检查用户是否已掌握某个知识点（精确匹配）
        
        Args:
            point_name: 知识点名称
        
        Returns:
            是否已掌握
        """
        return point_name in self.knowledge_points
    
    def has_course(self, course_name: str) -> bool:
        """
        检查用户是否已学过某个课程（精确匹配）
        
        Args:
            course_name: 课程名称
        
        Returns:
            是否已学过
        """
        return course_name in self.courses
    
    @classmethod
    def from_file(cls, file_path: str) -> 'UserProfile':
        """
        从YAML文件加载用户画像
        
        Args:
            file_path: YAML文件路径
        
        Returns:
            UserProfile实例
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"画像文件不存在: {file_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            profile_data = yaml.safe_load(f)
        
        return cls(profile_data)
    
    @classmethod
    def from_dict(cls, profile_dict: Dict) -> 'UserProfile':
        """
        从字典创建用户画像
        
        Args:
            profile_dict: 画像字典
        
        Returns:
            UserProfile实例
        """
        return cls(profile_dict)
    
    def _load_knowledge_points_from_courses(self):
        """
        从课程知识点文档中提取已掌握的知识点
        如果课程知识点文档不存在，会使用LLM生成
        """
        if not self.courses:
            return
        
        course_knowledge = CourseKnowledge()
        all_knowledge_points = []
        
        for course_name in self.courses:
            try:
                # 获取或生成课程知识点（如果不存在会自动生成）
                course_data = course_knowledge.get_or_generate_knowledge_points(
                    learning_goal=course_name,  # 使用课程名称作为学习目标来生成
                    course_name=course_name
                )
                
                # 提取知识点名称
                knowledge_points = course_data.get('knowledge_points', [])
                for point in knowledge_points:
                    point_name = point.get('name', '')
                    if point_name and point_name not in all_knowledge_points:
                        all_knowledge_points.append(point_name)
                
            except Exception as e:
                print(f"警告：加载课程 '{course_name}' 的知识点时出错: {str(e)}")
                continue
        
        self.knowledge_points = all_knowledge_points
    
    def to_dict(self) -> Dict:
        """
        转换为字典格式
        
        Returns:
            画像字典
        """
        return self.data
