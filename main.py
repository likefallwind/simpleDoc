"""
主程序
整合所有模块并输出培养方案
"""
import json
import yaml
import argparse
from pathlib import Path
from datetime import datetime
import config
from user_profile import UserProfile
from course_knowledge import CourseKnowledge
from prerequisite_analyzer import PrerequisiteAnalyzer
from learning_path import LearningPath


def generate_learning_plan(profile_path: str, output_path: str = None, output_format: str = 'json'):
    """
    生成学习方案
    
    Args:
        profile_path: 用户画像YAML文件路径
        output_path: 输出文件路径（可选，如果不提供则打印到控制台）
        output_format: 输出格式（'json' 或 'yaml'）
    """
    print("=" * 60)
    print("AI学习方案生成系统")
    print("=" * 60)
    
    # 1. 加载用户画像
    print("\n[步骤1] 加载用户画像...")
    try:
        print("  正在从课程文档中提取已掌握的知识点...")
        user_profile = UserProfile.from_file(profile_path)
        print(f"✓ 用户：{user_profile.name}")
        print(f"✓ 学习目标：{user_profile.learning_goal}")
        print(f"✓ 已学课程：{', '.join(user_profile.courses) if user_profile.courses else '无'}")
        print(f"✓ 已掌握知识点（从课程文档提取）：{len(user_profile.knowledge_points)} 个")
        if user_profile.knowledge_points:
            print(f"  {', '.join(user_profile.knowledge_points[:5])}{'...' if len(user_profile.knowledge_points) > 5 else ''}")
    except Exception as e:
        print(f"✗ 加载用户画像失败: {str(e)}")
        return
    
    # 2. 获取或生成课程知识点
    print(f"\n[步骤2] 获取课程知识点（目标：{user_profile.learning_goal}）...")
    course_knowledge = CourseKnowledge()
    try:
        course_data = course_knowledge.get_or_generate_knowledge_points(
            user_profile.learning_goal
        )
        knowledge_points = course_data.get('knowledge_points', [])
        print(f"✓ 找到 {len(knowledge_points)} 个知识点")
        
        if course_knowledge.course_exists(course_data.get('course_name', '')):
            print("✓ 使用已存在的课程知识点文件")
        else:
            print("✓ 生成新的课程知识点并已保存")
    except Exception as e:
        print(f"✗ 获取课程知识点失败: {str(e)}")
        return
    
    # 3. 分析前置依赖
    print(f"\n[步骤3] 分析知识点前置依赖...")
    print("  注意：此步骤可能需要较长时间，请耐心等待...")
    analyzer = PrerequisiteAnalyzer(user_profile, verbose=True)
    try:
        dependencies = analyzer.analyze_all_prerequisites(knowledge_points, recursive=True)
        print(f"\n✓ 分析完成，共 {len(dependencies)} 个知识点的依赖关系")
        
        # 获取所有需要学习的知识点（包括前置知识点）
        all_points = analyzer.get_all_knowledge_points(knowledge_points)
        print(f"✓ 包含前置知识点，共 {len(all_points)} 个知识点需要学习")
    except Exception as e:
        print(f"✗ 分析前置依赖失败: {str(e)}")
        return
    
    # 4. 排序学习路径
    print(f"\n[步骤4] 排序学习路径...")
    learning_path = LearningPath(user_profile)
    try:
        sorted_points = learning_path.sort_knowledge_points(all_points, dependencies)
        print(f"✓ 排序完成，共 {len(sorted_points)} 个知识点")
    except Exception as e:
        print(f"✗ 排序失败: {str(e)}")
        return
    
    # 5. 生成培养方案
    print(f"\n[步骤5] 生成培养方案...")
    plan = {
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
            'prerequisite_points': len(all_points) - len(knowledge_points)
        }
    }
    
    # 6. 输出结果
    print(f"\n[步骤6] 输出培养方案...")
    try:
        if output_format == 'yaml':
            output_content = yaml.dump(plan, allow_unicode=True, default_flow_style=False, sort_keys=False)
        else:
            output_content = json.dumps(plan, ensure_ascii=False, indent=2)
        
        # 确定输出文件路径
        if not output_path:
            # 自动生成文件名：基于用户名称和学习目标
            profiles_dir = Path(config.PROFILES_DIR)
            profiles_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成文件名：用户名_学习目标_时间戳.格式
            safe_name = user_profile.name.replace(' ', '_') if user_profile.name else 'user'
            safe_goal = user_profile.learning_goal.replace(' ', '_').replace('/', '_')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{safe_name}_{safe_goal}_{timestamp}.{output_format}"
            output_path = profiles_dir / filename
        else:
            # 如果指定了路径，确保目录存在
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存到文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output_content)
        print(f"✓ 培养方案已保存到: {output_path}")
        
        # 同时输出到控制台
        print("\n" + "=" * 60)
        print("培养方案")
        print("=" * 60)
        print(output_content)
        
    except Exception as e:
        print(f"✗ 输出失败: {str(e)}")
        return
    
    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='AI学习方案生成系统')
    parser.add_argument('profile', help='用户画像YAML文件路径')
    parser.add_argument('-o', '--output', help='输出文件路径（可选）')
    parser.add_argument('-f', '--format', choices=['json', 'yaml'], default='json',
                       help='输出格式（默认：json）')
    
    args = parser.parse_args()
    
    # 检查文件是否存在
    profile_path = Path(args.profile)
    if not profile_path.exists():
        print(f"错误：用户画像文件不存在: {args.profile}")
        return
    
    generate_learning_plan(str(profile_path), args.output, args.format)


if __name__ == '__main__':
    main()
