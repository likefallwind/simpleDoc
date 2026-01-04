"""
前置依赖分析模块
使用LLM判断前置知识点，通过维护路径列表避免循环
"""
from typing import List, Dict, Set
from llm_service import LLMService
import prompts
from user_profile import UserProfile


class PrerequisiteAnalyzer:
    """前置依赖分析器"""
    
    def __init__(self, user_profile: UserProfile, verbose: bool = True):
        """
        初始化前置依赖分析器
        
        Args:
            user_profile: 用户画像
            verbose: 是否输出详细进度信息
        """
        self.llm_service = LLMService()
        self.user_profile = user_profile
        self.dependencies: Dict[str, List[str]] = {}  # 知识点 -> 前置知识点列表
        self.analyzed_points: Set[str] = set()  # 已分析的知识点
        self.verbose = verbose
    
    def analyze_prerequisites_batch(self, knowledge_points: List[Dict], 
                                  batch_index: int = None, total_batches: int = None) -> Dict[str, List[str]]:
        """
        批量分析知识点的前置依赖
        
        Args:
            knowledge_points: 知识点列表，每个元素包含name和description
            batch_index: 当前批次索引（用于显示进度）
            total_batches: 总批次数（用于显示进度）
        
        Returns:
            依赖关系字典，key为知识点名称，value为前置知识点名称列表
        """
        # 过滤掉已经分析过的知识点
        points_to_analyze = [p for p in knowledge_points 
                           if p.get('name', '') not in self.analyzed_points]
        
        if not points_to_analyze:
            return {}
        
        # 显示进度
        if self.verbose:
            if batch_index is not None and total_batches is not None:
                print(f"  正在批量分析知识点 [批次 {batch_index}/{total_batches}]: {len(points_to_analyze)} 个知识点")
            else:
                print(f"  正在批量分析知识点: {len(points_to_analyze)} 个知识点")
            point_names = [p.get('name', '') for p in points_to_analyze]
            print(f"    知识点列表: {', '.join(point_names[:5])}{'...' if len(point_names) > 5 else ''}")
        
        # 获取用户背景信息
        user_background = self.user_profile.get_background_dict()
        
        # 生成批量分析提示词
        prompt = prompts.get_prerequisite_analysis_prompt_batch(points_to_analyze, user_background)
        
        # 调用LLM
        messages = [
            {'role': 'user', 'content': prompt}
        ]
        
        try:
            result = self.llm_service.chat_json(messages, stream=True)
            
            # 处理批量结果
            batch_dependencies = {}
            if 'results' in result:
                for item in result['results']:
                    point_name = item.get('knowledge_point', '')
                    if not point_name:
                        continue
                    
                    # 提取前置知识点
                    prerequisites = []
                    if 'prerequisites' in item:
                        for prereq in item['prerequisites']:
                            prereq_name = prereq.get('name', '')
                            if prereq_name:
                                # 检查用户是否已掌握
                                if not self.user_profile.has_knowledge_point(prereq_name):
                                    prerequisites.append(prereq_name)
                    
                    # 缓存结果
                    batch_dependencies[point_name] = prerequisites
                    self.dependencies[point_name] = prerequisites
                    self.analyzed_points.add(point_name)
            
            # 显示结果
            if self.verbose:
                total_prereqs = sum(len(prereqs) for prereqs in batch_dependencies.values())
                print(f"    ✓ 批量分析完成，共找到 {total_prereqs} 个前置知识点")
            
            return batch_dependencies
            
        except Exception as e:
            if self.verbose:
                print(f"    ✗ 批量分析知识点时出错: {str(e)}")
            # 出错时返回空字典，但标记为已分析（避免重复尝试）
            for point in points_to_analyze:
                point_name = point.get('name', '')
                if point_name:
                    self.dependencies[point_name] = []
                    self.analyzed_points.add(point_name)
            return {}
    
    def _analyze_recursive_batch(self, prerequisite_points: List[str], depth: int, 
                                max_depth: int, knowledge_points: List[Dict]):
        """
        批量递归分析前置知识点（限制深度，避免过度递归）
        
        Args:
            prerequisite_points: 需要分析的前置知识点名称列表
            depth: 当前递归深度
            max_depth: 最大递归深度
            knowledge_points: 所有知识点列表（用于上下文）
        """
        # 限制递归深度
        if depth >= max_depth:
            if self.verbose:
                print(f"  达到最大递归深度 {max_depth}，停止进一步分析")
            return
        
        # 过滤掉已经分析过的知识点
        points_to_analyze = [p for p in prerequisite_points 
                           if p not in self.analyzed_points]
        
        if not points_to_analyze:
            return
        
        # 显示递归分析进度
        if self.verbose:
            print(f"  递归分析第 {depth + 1} 层前置知识点: {len(points_to_analyze)} 个知识点")
            print(f"    知识点列表: {', '.join(points_to_analyze[:5])}{'...' if len(points_to_analyze) > 5 else ''}")
        
        # 将前置知识点转换为字典格式（可能没有描述）
        points_dict = [{'name': name, 'description': ''} for name in points_to_analyze]
        
        # 批量分析
        batch_dependencies = self.analyze_prerequisites_batch(points_dict)
        
        # 收集新发现的前置知识点
        new_prerequisites = []
        for prereqs in batch_dependencies.values():
            for prereq in prereqs:
                if prereq not in self.analyzed_points:
                    new_prerequisites.append(prereq)
        
        # 如果有新的前置知识点且未达到最大深度，继续递归
        if new_prerequisites and depth + 1 < max_depth:
            self._analyze_recursive_batch(new_prerequisites, depth + 1, max_depth, knowledge_points)
    
    def analyze_all_prerequisites(self, knowledge_points: List[Dict], 
                                  recursive: bool = True, max_depth: int = 2,
                                  batch_size: int = 5) -> Dict[str, List[str]]:
        """
        分析所有知识点的前置依赖（批量分析，限制递归深度）
        
        Args:
            knowledge_points: 知识点列表
            recursive: 是否递归分析前置知识点的前置依赖
            max_depth: 最大递归深度（默认2层）
            batch_size: 每批分析的知识点数量（默认5个）
        
        Returns:
            依赖关系字典，key为知识点名称，value为前置知识点名称列表
        """
        total = len(knowledge_points)
        
        if self.verbose:
            print(f"  开始分析 {total} 个知识点的前置依赖...")
            print(f"  批量大小: {batch_size}，最大递归深度: {max_depth}")
        
        # 批量分析初始知识点的直接前置依赖
        batches = []
        for i in range(0, total, batch_size):
            batch = knowledge_points[i:i + batch_size]
            batches.append(batch)
        
        total_batches = len(batches)
        for idx, batch in enumerate(batches, 1):
            self.analyze_prerequisites_batch(batch, batch_index=idx, total_batches=total_batches)
        
        if self.verbose:
            print(f"  初始知识点分析完成，已分析 {len(self.analyzed_points)} 个知识点")
        
        # 如果启用递归，继续分析前置知识点的前置依赖
        if recursive:
            if self.verbose:
                print(f"  开始递归分析前置知识点（最多 {max_depth} 层）...")
            
            # 收集所有需要递归分析的知识点（前置知识点）
            points_to_analyze = {p.get('name', '') for p in knowledge_points}
            all_prerequisites = []
            
            for point_name, prereqs in self.dependencies.items():
                for prereq in prereqs:
                    if prereq not in self.analyzed_points and prereq not in points_to_analyze:
                        all_prerequisites.append(prereq)
            
            # 去重
            all_prerequisites = list(set(all_prerequisites))
            
            if all_prerequisites:
                # 批量递归分析
                self._analyze_recursive_batch(all_prerequisites, depth=0, 
                                             max_depth=max_depth, 
                                             knowledge_points=knowledge_points)
            
            if self.verbose:
                print(f"  递归分析完成，共分析了 {len(self.analyzed_points)} 个知识点（包括前置知识点）")
        
        return self.dependencies
    
    
    def get_all_knowledge_points(self, initial_points: List[Dict]) -> List[Dict]:
        """
        获取所有需要学习的知识点（包括前置知识点）
        
        Args:
            initial_points: 初始知识点列表
        
        Returns:
            所有知识点列表（去重）
        """
        # 收集所有知识点名称（使用set自动去重）
        all_point_names = set()
        
        # 添加初始知识点
        for point in initial_points:
            name = point.get('name', '')
            if name:
                all_point_names.add(name)
        
        # 添加前置知识点
        for prereqs in self.dependencies.values():
            all_point_names.update(prereqs)
        
        # 构建知识点字典（初始知识点优先，前置知识点可能只有名称）
        point_dict = {p.get('name', ''): p for p in initial_points}
        
        result = []
        for name in all_point_names:
            if name in point_dict:
                result.append(point_dict[name])
            else:
                # 前置知识点，只有名称
                result.append({'name': name, 'description': ''})
        
        return result
