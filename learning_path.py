"""
学习路径排序模块
将所有知识点交给LLM进行排序（3次取平均值）
"""
from typing import List, Dict
from collections import defaultdict
import config
from llm_service import LLMService
import prompts
from user_profile import UserProfile


class LearningPath:
    """学习路径排序器"""
    
    def __init__(self, user_profile: UserProfile):
        """
        初始化学习路径排序器
        
        Args:
            user_profile: 用户画像
        """
        self.llm_service = LLMService()
        self.user_profile = user_profile
        self.max_points = config.MAX_KNOWLEDGE_POINTS
        self.sort_retry_count = config.SORT_RETRY_COUNT
    
    def check_point_limit(self, knowledge_points: List[Dict]) -> List[Dict]:
        """
        检查知识点数量限制
        
        Args:
            knowledge_points: 知识点列表
        
        Returns:
            处理后的知识点列表（如果超过限制则截断或提示）
        """
        if len(knowledge_points) > self.max_points:
            print(f"警告：知识点数量({len(knowledge_points)})超过上限({self.max_points})，将截断到前{self.max_points}个")
            return knowledge_points[:self.max_points]
        return knowledge_points
    
    def _calculate_average_rankings(self, all_results: List[List[Dict]]) -> Dict[str, float]:
        """
        计算平均排名
        
        Args:
            all_results: 多次排序的结果列表
        
        Returns:
            知识点名称到平均排名的字典
        """
        # 统计每个知识点在所有排序中的位置
        point_positions = defaultdict(list)
        
        for result in all_results:
            sorted_points = result.get('sorted_knowledge_points', [])
            for idx, point in enumerate(sorted_points, 1):
                point_name = point.get('name', '')
                if point_name:
                    point_positions[point_name].append(idx)
        
        # 计算平均位置
        avg_rankings = {}
        for point_name, positions in point_positions.items():
            avg_rankings[point_name] = sum(positions) / len(positions)
        
        return avg_rankings
    
    def sort_knowledge_points(self, knowledge_points: List[Dict], 
                             dependencies: Dict[str, List[str]]) -> List[Dict]:
        """
        对知识点进行排序（调用LLM多次取平均值）
        
        Args:
            knowledge_points: 知识点列表
            dependencies: 依赖关系字典
        
        Returns:
            排序后的知识点列表
        """
        # 检查数量限制
        knowledge_points = self.check_point_limit(knowledge_points)
        
        if len(knowledge_points) == 0:
            return []
        
        if len(knowledge_points) == 1:
            return knowledge_points
        
        # 获取用户背景信息
        user_background = self.user_profile.get_background_dict()
        
        # 生成提示词
        prompt = prompts.get_learning_path_sorting_prompt(
            knowledge_points,
            dependencies,
            user_background
        )
        
        messages = [
            {'role': 'user', 'content': prompt}
        ]
        
        # 多次调用LLM
        print(f"正在调用LLM进行排序（共{self.sort_retry_count}次）...")
        all_results = []
        
        for i in range(self.sort_retry_count):
            try:
                result = self.llm_service.chat_json(messages, stream=True)
                all_results.append(result)
                print(f"第{i+1}次排序完成")
            except Exception as e:
                print(f"第{i+1}次排序失败: {str(e)}")
                # 如果某次失败，继续尝试其他次
        
        if not all_results:
            raise Exception("所有排序尝试都失败了")
        
        # 计算平均排名
        avg_rankings = self._calculate_average_rankings(all_results)
        
        # 创建知识点名称到完整信息的映射
        point_dict = {p.get('name', ''): p for p in knowledge_points}
        
        # 按平均排名排序
        sorted_points = []
        for point_name, avg_rank in sorted(avg_rankings.items(), key=lambda x: x[1]):
            if point_name in point_dict:
                point_info = point_dict[point_name].copy()
                point_info['order'] = len(sorted_points) + 1
                point_info['avg_rank'] = round(avg_rank, 2)
                sorted_points.append(point_info)
        
        # 处理可能遗漏的知识点（在排序结果中未出现的）
        sorted_names = {p.get('name', '') for p in sorted_points}
        for point in knowledge_points:
            point_name = point.get('name', '')
            if point_name and point_name not in sorted_names:
                # 添加到末尾
                point_info = point.copy()
                point_info['order'] = len(sorted_points) + 1
                point_info['avg_rank'] = len(knowledge_points) + 1  # 默认排名
                sorted_points.append(point_info)
        
        return sorted_points
