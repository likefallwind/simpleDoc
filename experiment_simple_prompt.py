"""
实验脚本：对比简单prompt方案 vs 原版prompt方案
不修改原有代码，独立运行实验
"""
import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import config
from user_profile import UserProfile
from course_knowledge import CourseKnowledge
from prerequisite_analyzer import PrerequisiteAnalyzer
from learning_path import LearningPath
from llm_service import LLMService


# ==================== 简单Prompt方案 ====================

def get_simple_knowledge_points_prompt(learning_goal: str, course_name: str = None) -> str:
    """简单版知识点提取提示词"""
    prompt = f"""请为学习目标"{learning_goal}"提取知识点。

请以JSON格式输出：
{{
    "course_name": "课程名称",
    "course_description": "简短描述",
    "knowledge_points": [
        {{
            "name": "知识点名称",
            "description": "描述"
        }}
    ]
}}
请直接输出JSON。"""
    return prompt


def get_simple_prerequisite_prompt(knowledge_points: List[Dict], user_background: Dict = None) -> str:
    """简单版前置依赖分析提示词"""
    points_text = "知识点列表：\n"
    for i, point in enumerate(knowledge_points, 1):
        name = point.get('name', '')
        desc = point.get('description', '')
        points_text += f"{i}. {name} ({desc})\n"
    
    prompt = f"""请分析以下知识点，找出学习它们需要的前置知识点。

{points_text}

请以JSON格式输出：
{{
    "results": [
        {{
            "knowledge_point": "知识点名称",
            "prerequisites": [
                {{
                    "name": "前置知识点名称",
                    "description": "描述",
                    "reason": "原因"
                }}
            ]
        }}
    ]
}}
请直接输出JSON。"""
    return prompt


def get_simple_sorting_prompt(knowledge_points: List[Dict], 
                             dependencies: Dict[str, List[str]] = None,
                             user_background: Dict = None) -> str:
    """简单版学习路径排序提示词"""
    points_text = "知识点列表：\n"
    for i, point in enumerate(knowledge_points, 1):
        name = point.get('name', '')
        points_text += f"{i}. {name}\n"
    
    deps_text = ""
    if dependencies:
        deps_text = "\n依赖关系：\n"
        for point, prereqs in dependencies.items():
            if prereqs:
                for req in prereqs:
                    deps_text += f"- {req} -> {point}\n"
    
    prompt = f"""请对以下知识点进行排序。

{points_text}{deps_text}

请以JSON输出：
{{
    "sorted_knowledge_points": [
        {{
            "name": "知识点名称",
            "order": 1,
            "reason": "排序理由"
        }}
    ]
}}"""
    return prompt


# ==================== 实验类（使用简单Prompt） ====================

class SimplePromptCourseKnowledge(CourseKnowledge):
    """使用简单prompt的课程知识点管理类"""
    
    def generate_knowledge_points(self, learning_goal: str, course_name: str = None) -> Dict:
        """使用简单prompt生成知识点"""
        if not course_name:
            course_name = learning_goal
        
        prompt = get_simple_knowledge_points_prompt(learning_goal, course_name)
        messages = [{'role': 'user', 'content': prompt}]
        result = self.llm_service.chat_json(messages, stream=True)
        
        if 'knowledge_points' not in result:
            raise ValueError("LLM返回的数据格式不正确，缺少'knowledge_points'字段")
        return result


class SimplePromptPrerequisiteAnalyzer(PrerequisiteAnalyzer):
    """使用简单prompt的前置依赖分析器"""
    
    def analyze_prerequisites_batch(self, knowledge_points: List[Dict], 
                                  batch_index: int = None, total_batches: int = None) -> Dict[str, List[str]]:
        """使用简单prompt批量分析前置依赖"""
        points_to_analyze = [p for p in knowledge_points 
                           if p.get('name', '') not in self.analyzed_points]
        
        if not points_to_analyze:
            return {}
        
        if self.verbose:
            if batch_index is not None and total_batches is not None:
                print(f"  正在批量分析知识点 [批次 {batch_index}/{total_batches}]: {len(points_to_analyze)} 个知识点")
            else:
                print(f"  正在批量分析知识点: {len(points_to_analyze)} 个知识点")
        
        user_background = self.user_profile.get_background_dict()
        prompt = get_simple_prerequisite_prompt(points_to_analyze, user_background)
        
        messages = [{'role': 'user', 'content': prompt}]
        
        try:
            result = self.llm_service.chat_json(messages, stream=True)
            
            batch_dependencies = {}
            if 'results' in result:
                for item in result['results']:
                    point_name = item.get('knowledge_point', '')
                    if not point_name:
                        continue
                    
                    prerequisites = []
                    if 'prerequisites' in item:
                        for prereq in item['prerequisites']:
                            prereq_name = prereq.get('name', '')
                            if prereq_name:
                                if not self.user_profile.has_knowledge_point(prereq_name):
                                    prerequisites.append(prereq_name)
                                    prereq_desc = prereq.get('description', '')
                                    if not prereq_desc:
                                        prereq_desc = prereq.get('reason', '')
                                    if prereq_name not in self.prerequisite_descriptions or not self.prerequisite_descriptions[prereq_name]:
                                        self.prerequisite_descriptions[prereq_name] = prereq_desc
                    
                    batch_dependencies[point_name] = prerequisites
                    self.dependencies[point_name] = prerequisites
                    self.analyzed_points.add(point_name)
            
            if self.verbose:
                total_prereqs = sum(len(prereqs) for prereqs in batch_dependencies.values())
                print(f"    ✓ 批量分析完成，共找到 {total_prereqs} 个前置知识点")
            
            return batch_dependencies
            
        except Exception as e:
            if self.verbose:
                print(f"    ✗ 批量分析知识点时出错: {str(e)}")
            for point in points_to_analyze:
                point_name = point.get('name', '')
                if point_name:
                    self.dependencies[point_name] = []
                    self.analyzed_points.add(point_name)
            return {}


class SimplePromptLearningPath(LearningPath):
    """使用简单prompt的学习路径排序器"""
    
    def sort_knowledge_points(self, knowledge_points: List[Dict], 
                             dependencies: Dict[str, List[str]]) -> List[Dict]:
        """使用简单prompt进行排序"""
        knowledge_points = self.check_point_limit(knowledge_points)
        
        if len(knowledge_points) == 0:
            return []
        if len(knowledge_points) == 1:
            return knowledge_points
        
        user_background = self.user_profile.get_background_dict()
        prompt = get_simple_sorting_prompt(knowledge_points, dependencies, user_background)
        
        messages = [{'role': 'user', 'content': prompt}]
        
        print(f"正在调用LLM进行排序（共{self.sort_retry_count}次）...")
        all_results = []
        
        for i in range(self.sort_retry_count):
            try:
                result = self.llm_service.chat_json(messages, stream=True)
                all_results.append(result)
                print(f"第{i+1}次排序完成")
            except Exception as e:
                print(f"第{i+1}次排序失败: {str(e)}")
        
        if not all_results:
            raise Exception("所有排序尝试都失败了")
        
        avg_rankings = self._calculate_average_rankings(all_results)
        point_dict = {p.get('name', ''): p for p in knowledge_points}
        
        sorted_points = []
        for point_name, avg_rank in sorted(avg_rankings.items(), key=lambda x: x[1]):
            if point_name in point_dict:
                point_info = point_dict[point_name].copy()
                point_info['order'] = len(sorted_points) + 1
                point_info['avg_rank'] = round(avg_rank, 2)
                sorted_points.append(point_info)
        
        sorted_names = {p.get('name', '') for p in sorted_points}
        for point in knowledge_points:
            point_name = point.get('name', '')
            if point_name and point_name not in sorted_names:
                point_info = point.copy()
                point_info['order'] = len(sorted_points) + 1
                point_info['avg_rank'] = len(knowledge_points) + 1
                sorted_points.append(point_info)
        
        return sorted_points


# ==================== 实验运行函数 ====================

def run_experiment(profile_path: str, use_simple_prompt: bool = False, output_dir: str = "experiments"):
    """
    运行实验
    
    Args:
        profile_path: 用户画像文件路径
        use_simple_prompt: 是否使用简单prompt
        output_dir: 输出目录
    """
    prompt_type = "simple" if use_simple_prompt else "original"
    print("=" * 60)
    print(f"实验运行：{'简单Prompt方案' if use_simple_prompt else '原版Prompt方案'}")
    print("=" * 60)
    
    # 加载用户画像
    print("\n[步骤1] 加载用户画像...")
    try:
        user_profile = UserProfile.from_file(profile_path)
        print(f"✓ 用户：{user_profile.name}")
        print(f"✓ 学习目标：{user_profile.learning_goal}")
        print(f"✓ 已学课程：{', '.join(user_profile.courses) if user_profile.courses else '无'}")
    except Exception as e:
        print(f"✗ 加载用户画像失败: {str(e)}")
        return None
    
    # 获取课程知识点（使用不同的类）
    print(f"\n[步骤2] 获取课程知识点...")
    if use_simple_prompt:
        course_knowledge = SimplePromptCourseKnowledge()
    else:
        course_knowledge = CourseKnowledge()
    
    try:
        course_data = course_knowledge.get_or_generate_knowledge_points(
            user_profile.learning_goal
        )
        knowledge_points = course_data.get('knowledge_points', [])
        print(f"✓ 找到 {len(knowledge_points)} 个知识点")
    except Exception as e:
        print(f"✗ 获取课程知识点失败: {str(e)}")
        return None
    
    # 分析前置依赖
    print(f"\n[步骤3] 分析知识点前置依赖...")
    if use_simple_prompt:
        analyzer = SimplePromptPrerequisiteAnalyzer(user_profile, verbose=True)
    else:
        analyzer = PrerequisiteAnalyzer(user_profile, verbose=True)
    
    try:
        dependencies = analyzer.analyze_all_prerequisites(knowledge_points, recursive=True)
        print(f"\n✓ 分析完成，共 {len(dependencies)} 个知识点的依赖关系")
        
        all_points = analyzer.get_all_knowledge_points(knowledge_points)
        print(f"✓ 包含前置知识点，共 {len(all_points)} 个知识点需要学习")
    except Exception as e:
        print(f"✗ 分析前置依赖失败: {str(e)}")
        return None
    
    # 排序学习路径
    print(f"\n[步骤4] 排序学习路径...")
    if use_simple_prompt:
        learning_path = SimplePromptLearningPath(user_profile)
    else:
        learning_path = LearningPath(user_profile)
    
    try:
        sorted_points = learning_path.sort_knowledge_points(all_points, dependencies)
        print(f"✓ 排序完成，共 {len(sorted_points)} 个知识点")
    except Exception as e:
        print(f"✗ 排序失败: {str(e)}")
        return None
    
    # 生成结果
    result = {
        'prompt_type': prompt_type,
        'user': {
            'name': user_profile.name,
            'learning_goal': user_profile.learning_goal
        },
        'course': {
            'name': course_data.get('course_name', ''),
            'description': course_data.get('course_description', '')
        },
        'learning_path': sorted_points,
        'dependencies': dependencies,
        'statistics': {
            'total_points': len(sorted_points),
            'initial_points': len(knowledge_points),
            'prerequisite_points': len(all_points) - len(knowledge_points),
            'dependency_count': len(dependencies)
        }
    }
    
    # 保存结果
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    safe_name = user_profile.name.replace(' ', '_') if user_profile.name else 'user'
    safe_goal = user_profile.learning_goal.replace(' ', '_').replace('/', '_')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{prompt_type}_{safe_name}_{safe_goal}_{timestamp}.json"
    file_path = output_path / filename
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ 结果已保存到: {file_path}")
    
    return result


def compare_results(original_result: Dict, simple_result: Dict):
    """
    对比两种方案的结果
    
    Args:
        original_result: 原版方案结果
        simple_result: 简单方案结果
    """
    print("\n" + "=" * 60)
    print("实验结果对比")
    print("=" * 60)
    
    # 统计信息对比
    orig_stats = original_result.get('statistics', {})
    simple_stats = simple_result.get('statistics', {})
    
    print("\n【统计信息对比】")
    print(f"{'指标':<30} {'原版方案':<15} {'简单方案':<15} {'差异':<15}")
    print("-" * 75)
    
    metrics = [
        ('初始知识点数', 'initial_points'),
        ('前置知识点数', 'prerequisite_points'),
        ('总知识点数', 'total_points'),
        ('依赖关系数', 'dependency_count')
    ]
    
    for label, key in metrics:
        orig_val = orig_stats.get(key, 0)
        simple_val = simple_stats.get(key, 0)
        diff = simple_val - orig_val
        diff_str = f"{diff:+d}" if diff != 0 else "0"
        print(f"{label:<30} {orig_val:<15} {simple_val:<15} {diff_str:<15}")
    
    # 知识点对比
    print("\n【知识点对比】")
    orig_points = {p.get('name', '') for p in original_result.get('learning_path', [])}
    simple_points = {p.get('name', '') for p in simple_result.get('learning_path', [])}
    
    only_orig = orig_points - simple_points
    only_simple = simple_points - orig_points
    common = orig_points & simple_points
    
    print(f"原版方案独有知识点: {len(only_orig)} 个")
    if only_orig:
        for point in list(only_orig)[:5]:
            print(f"  - {point}")
        if len(only_orig) > 5:
            print(f"  ... 还有 {len(only_orig) - 5} 个")
    
    print(f"\n简单方案独有知识点: {len(only_simple)} 个")
    if only_simple:
        for point in list(only_simple)[:5]:
            print(f"  - {point}")
        if len(only_simple) > 5:
            print(f"  ... 还有 {len(only_simple) - 5} 个")
    
    print(f"\n共同知识点: {len(common)} 个")
    
    # 排序对比（对共同知识点）
    print("\n【排序对比（共同知识点）】")
    orig_path = {p.get('name', ''): p.get('order', 0) for p in original_result.get('learning_path', [])}
    simple_path = {p.get('name', ''): p.get('order', 0) for p in simple_result.get('learning_path', [])}
    
    common_sorted = sorted(common, key=lambda x: orig_path.get(x, 999))
    print(f"{'知识点':<40} {'原版排序':<15} {'简单排序':<15} {'差异':<15}")
    print("-" * 85)
    
    rank_diffs = []
    for point in common_sorted[:10]:  # 只显示前10个
        orig_order = orig_path.get(point, 0)
        simple_order = simple_path.get(point, 0)
        diff = simple_order - orig_order
        rank_diffs.append(abs(diff))
        point_display = point[:38] + "..." if len(point) > 40 else point
        print(f"{point_display:<40} {orig_order:<15} {simple_order:<15} {diff:+d}")
    
    if len(common_sorted) > 10:
        print(f"... 还有 {len(common_sorted) - 10} 个知识点")
    
    if rank_diffs:
        avg_diff = sum(rank_diffs) / len(rank_diffs)
        print(f"\n平均排序差异: {avg_diff:.2f} 位")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Prompt方案对比实验')
    parser.add_argument('profile', help='用户画像YAML文件路径')
    parser.add_argument('--output-dir', default='experiments', help='实验结果输出目录（默认：experiments）')
    parser.add_argument('--compare', action='store_true', help='运行两种方案并对比（需要运行两次）')
    parser.add_argument('--simple-only', action='store_true', help='只运行简单prompt方案')
    parser.add_argument('--original-only', action='store_true', help='只运行原版prompt方案')
    
    args = parser.parse_args()
    
    # 如果指定了compare，运行两种方案
    if args.compare:
        print("=" * 60)
        print("开始对比实验：将运行两种方案")
        print("=" * 60)
        
        # 运行原版方案
        print("\n" + "=" * 60)
        print("【实验1】原版Prompt方案")
        print("=" * 60)
        original_result = run_experiment(args.profile, use_simple_prompt=False, output_dir=args.output_dir)
        
        if not original_result:
            print("原版方案运行失败，无法进行对比")
            return
        
        # 运行简单方案
        print("\n" + "=" * 60)
        print("【实验2】简单Prompt方案")
        print("=" * 60)
        simple_result = run_experiment(args.profile, use_simple_prompt=True, output_dir=args.output_dir)
        
        if not simple_result:
            print("简单方案运行失败，无法进行对比")
            return
        
        # 对比结果
        compare_results(original_result, simple_result)
        
        # 保存对比结果
        output_path = Path(args.output_dir)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        comparison_file = output_path / f"comparison_{timestamp}.json"
        
        comparison_data = {
            'timestamp': timestamp,
            'original': original_result,
            'simple': simple_result
        }
        
        with open(comparison_file, 'w', encoding='utf-8') as f:
            json.dump(comparison_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✓ 对比结果已保存到: {comparison_file}")
    
    elif args.simple_only:
        run_experiment(args.profile, use_simple_prompt=True, output_dir=args.output_dir)
    
    elif args.original_only:
        run_experiment(args.profile, use_simple_prompt=False, output_dir=args.output_dir)
    
    else:
        # 默认只运行原版方案
        print("提示：使用 --compare 参数可以同时运行两种方案并对比")
        run_experiment(args.profile, use_simple_prompt=False, output_dir=args.output_dir)


if __name__ == '__main__':
    main()

