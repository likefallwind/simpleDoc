"""
教案生成模块
基于知识点和用户画像生成个性化教案
"""
from typing import List, Dict
from pathlib import Path
import config
from llm_service import LLMService
import prompts
from user_profile import UserProfile


class LessonGenerator:
    """教案生成器"""
    
    def __init__(self, user_profile: UserProfile):
        """
        初始化教案生成器
        
        Args:
            user_profile: 用户画像
        """
        self.llm_service = LLMService()
        self.user_profile = user_profile
        self.lessons_dir = Path(config.LESSONS_DIR)
        self.lessons_dir.mkdir(parents=True, exist_ok=True)
    
    def get_lesson_file_path(self, knowledge_point_name: str) -> Path:
        """
        获取教案文件路径
        
        Args:
            knowledge_point_name: 知识点名称
        
        Returns:
            文件路径
        """
        # 清理文件名中的特殊字符
        safe_name = knowledge_point_name.replace('/', '_').replace('\\', '_').replace(':', '_')
        safe_name = safe_name.replace('?', '').replace('*', '').replace('"', '').replace('<', '').replace('>', '')
        filename = f"{safe_name}.md"
        return self.lessons_dir / filename
    
    def lesson_exists(self, knowledge_point_name: str) -> bool:
        """
        检查教案文件是否存在
        
        Args:
            knowledge_point_name: 知识点名称
        
        Returns:
            是否存在
        """
        file_path = self.get_lesson_file_path(knowledge_point_name)
        return file_path.exists()
    
    def get_related_knowledge_points(self, point_name: str, 
                                     learning_path: List[Dict],
                                     dependencies: Dict[str, List[str]]) -> Dict:
        """
        获取知识点的相关关系信息
        
        Args:
            point_name: 知识点名称
            learning_path: 学习路径（排序后的知识点列表）
            dependencies: 依赖关系字典
        
        Returns:
            包含前置、后续、位置等信息的字典
        """
        # 找到当前知识点在学习路径中的位置
        current_index = -1
        for idx, point in enumerate(learning_path):
            if point.get('name', '') == point_name:
                current_index = idx
                break
        
        # 获取前置知识点
        prerequisites = dependencies.get(point_name, [])
        
        # 获取后续知识点（哪些知识点依赖当前知识点）
        subsequent_points = []
        for other_point, prereqs in dependencies.items():
            if point_name in prereqs:
                subsequent_points.append(other_point)
        
        # 获取前一个和后一个知识点
        prev_point = None
        next_point = None
        if current_index > 0:
            prev_point = learning_path[current_index - 1].get('name', '')
        if current_index >= 0 and current_index < len(learning_path) - 1:
            next_point = learning_path[current_index + 1].get('name', '')
        
        return {
            'order': current_index + 1 if current_index >= 0 else None,
            'total': len(learning_path),
            'prerequisites': prerequisites,
            'subsequent_points': subsequent_points,
            'prev_point': prev_point,
            'next_point': next_point
        }
    
    def generate_lesson(self, knowledge_point: Dict, 
                       learning_path: List[Dict],
                       dependencies: Dict[str, List[str]]) -> str:
        """
        生成单个知识点的教案
        
        Args:
            knowledge_point: 知识点字典，包含name和description
            learning_path: 学习路径（排序后的知识点列表）
            dependencies: 依赖关系字典
        
        Returns:
            教案内容（Markdown格式）
        """
        point_name = knowledge_point.get('name', '')
        point_desc = knowledge_point.get('description', '')
        
        # 获取相关知识点信息
        related_info = self.get_related_knowledge_points(point_name, learning_path, dependencies)
        
        # 获取用户背景信息
        user_background = self.user_profile.get_background_dict()
        
        # 生成提示词
        prompt = prompts.get_lesson_generation_prompt(
            knowledge_point,
            related_info,
            user_background,
            self.user_profile.learning_goal
        )
        
        # 调用LLM
        messages = [
            {'role': 'user', 'content': prompt}
        ]
        
        try:
            lesson_content = self.llm_service.chat(messages, stream=True)
            return lesson_content
        except Exception as e:
            raise Exception(f"生成教案失败: {str(e)}")
    
    def save_lesson(self, knowledge_point_name: str, lesson_content: str):
        """
        保存教案到文件
        
        Args:
            knowledge_point_name: 知识点名称
            lesson_content: 教案内容
        """
        file_path = self.get_lesson_file_path(knowledge_point_name)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(lesson_content)
    
    def generate_all_lessons(self, learning_path: List[Dict],
                            dependencies: Dict[str, List[str]],
                            verbose: bool = True) -> List[str]:
        """
        生成所有知识点的教案
        
        Args:
            learning_path: 学习路径（排序后的知识点列表）
            dependencies: 依赖关系字典
            verbose: 是否显示详细进度
        
        Returns:
            生成的教案文件路径列表
        """
        generated_files = []
        total = len(learning_path)
        
        if verbose:
            print(f"  开始生成 {total} 个知识点的教案...")
        
        for idx, point in enumerate(learning_path, 1):
            point_name = point.get('name', '')
            
            if verbose:
                print(f"  正在生成教案 [{idx}/{total}]: {point_name}")
            
            try:
                # 检查是否已存在
                if self.lesson_exists(point_name):
                    if verbose:
                        print(f"    ⚠ 教案已存在，跳过")
                    continue
                
                # 生成教案
                lesson_content = self.generate_lesson(point, learning_path, dependencies)
                
                # 保存教案
                self.save_lesson(point_name, lesson_content)
                file_path = self.get_lesson_file_path(point_name)
                generated_files.append(str(file_path))
                
                if verbose:
                    print(f"    ✓ 教案已保存: {file_path.name}")
                    
            except Exception as e:
                if verbose:
                    print(f"    ✗ 生成教案失败: {str(e)}")
                continue
        
        if verbose:
            print(f"  教案生成完成，共生成 {len(generated_files)} 个教案文件")
        
        return generated_files

