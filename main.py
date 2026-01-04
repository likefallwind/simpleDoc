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
from lesson_generator import LessonGenerator


def generate_learning_plan(profile_path: str, output_path: str = None, output_format: str = 'json', 
                           generate_lessons: bool = False):
    """
    生成学习方案
    
    Args:
        profile_path: 用户画像YAML文件路径
        output_path: 输出文件路径（可选，如果不提供则打印到控制台）
        output_format: 输出格式（'json' 或 'yaml'）
        generate_lessons: 是否生成知识点教案（默认False）
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
    
    # 6. 生成教案（可选）
    if generate_lessons:
        print(f"\n[步骤6] 生成知识点教案...")
        lesson_generator = LessonGenerator(user_profile)
        try:
            lesson_files = lesson_generator.generate_all_lessons(
                sorted_points, 
                dependencies, 
                verbose=True
            )
            print(f"\n✓ 教案生成完成，共生成 {len(lesson_files)} 个教案文件")
            if lesson_files:
                print(f"  教案保存目录: {config.LESSONS_DIR}")
        except Exception as e:
            print(f"✗ 生成教案失败: {str(e)}")
            # 教案生成失败不影响主流程，继续执行
    else:
        print(f"\n[步骤6] 跳过教案生成（使用 --generate-lessons 参数可生成教案）")
    
    # 7. 输出结果
    print(f"\n[步骤7] 输出培养方案...")
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


def test_knowledge_points(profile_path: str, learning_goal: str = None, output_path: str = None):
    """
    快速测试知识点生成（不进行依赖分析和排序）
    
    Args:
        profile_path: 用户画像YAML文件路径（可选，如果不提供则只使用learning_goal）
        learning_goal: 学习目标（如果提供profile_path则从文件中读取）
        output_path: 输出文件路径（可选，如果不提供则只打印到控制台）
    """
    print("=" * 60)
    print("知识点生成测试（快速模式）")
    print("=" * 60)
    
    # 确定学习目标
    if profile_path:
        try:
            user_profile = UserProfile.from_file(profile_path)
            learning_goal = user_profile.learning_goal
            print(f"\n从用户画像读取学习目标: {learning_goal}")
        except Exception as e:
            print(f"✗ 加载用户画像失败: {str(e)}")
            if not learning_goal:
                print("错误：请提供学习目标或有效的用户画像文件")
                return
    elif not learning_goal:
        print("错误：请提供学习目标（--goal）或用户画像文件（--profile）")
        return
    
    # 生成知识点
    print(f"\n[测试] 生成课程知识点（目标：{learning_goal}）...")
    course_knowledge = CourseKnowledge()
    try:
        course_data = course_knowledge.get_or_generate_knowledge_points(learning_goal)
        knowledge_points = course_data.get('knowledge_points', [])
        
        print(f"\n✓ 生成完成")
        print(f"课程名称: {course_data.get('course_name', '')}")
        print(f"课程描述: {course_data.get('course_description', '')}")
        print(f"\n知识点列表（共 {len(knowledge_points)} 个）:")
        print("-" * 60)
        for i, point in enumerate(knowledge_points, 1):
            name = point.get('name', '')
            desc = point.get('description', '')
            print(f"{i}. {name}")
            if desc:
                print(f"   {desc}")
            print()
        
        # 输出到文件（如果需要）
        if output_path:
            import json
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(course_data, f, ensure_ascii=False, indent=2)
            print(f"✓ 结果已保存到: {output_path}")
        
        # 显示文件位置
        course_name = course_data.get('course_name', learning_goal)
        file_path = course_knowledge.get_course_file_path(course_name)
        print(f"\n知识点文件位置: {file_path}")
        
    except Exception as e:
        print(f"✗ 生成知识点失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


def generate_lessons_from_plan(plan_path: str, profile_path: str = None):
    """
    基于已有的学习方案生成教案
    
    Args:
        plan_path: 学习方案文件路径（JSON或YAML）
        profile_path: 用户画像文件路径（可选，如果不提供则从学习方案中提取）
    """
    print("=" * 60)
    print("基于学习方案生成教案")
    print("=" * 60)
    
    # 1. 加载学习方案
    print(f"\n[步骤1] 加载学习方案...")
    plan_file = Path(plan_path)
    if not plan_file.exists():
        print(f"✗ 学习方案文件不存在: {plan_path}")
        return
    
    try:
        with open(plan_file, 'r', encoding='utf-8') as f:
            if plan_file.suffix.lower() == '.yaml' or plan_file.suffix.lower() == '.yml':
                plan_data = yaml.safe_load(f)
            else:
                plan_data = json.load(f)
        
        print(f"✓ 学习方案加载成功")
    except Exception as e:
        print(f"✗ 加载学习方案失败: {str(e)}")
        return
    
    # 2. 提取信息
    print(f"\n[步骤2] 提取学习方案信息...")
    try:
        user_info = plan_data.get('user', {})
        learning_path = plan_data.get('learning_path', [])
        dependencies = plan_data.get('dependencies', {})
        learning_goal = user_info.get('learning_goal', '')
        user_name = user_info.get('name', '')
        
        if not learning_path:
            print(f"✗ 学习方案中缺少知识点列表")
            return
        
        print(f"✓ 找到 {len(learning_path)} 个知识点")
        print(f"✓ 学习目标: {learning_goal}")
    except Exception as e:
        print(f"✗ 提取信息失败: {str(e)}")
        return
    
    # 3. 加载或创建用户画像
    print(f"\n[步骤3] 加载用户画像...")
    try:
        if profile_path:
            user_profile = UserProfile.from_file(profile_path)
            print(f"✓ 从文件加载用户画像: {user_profile.name}")
        else:
            # 从学习方案中创建用户画像
            profile_dict = {
                'user': {
                    'name': user_name,
                    'background': {
                        'courses': []
                    },
                    'learning_goal': learning_goal
                }
            }
            user_profile = UserProfile.from_dict(profile_dict)
            print(f"✓ 从学习方案中提取用户信息: {user_profile.name}")
            print(f"  注意：未提供用户画像文件，将使用基础信息生成教案")
    except Exception as e:
        print(f"✗ 加载用户画像失败: {str(e)}")
        return
    
    # 4. 生成教案
    print(f"\n[步骤4] 生成知识点教案...")
    lesson_generator = LessonGenerator(user_profile)
    try:
        lesson_files = lesson_generator.generate_all_lessons(
            learning_path,
            dependencies,
            verbose=True
        )
        print(f"\n✓ 教案生成完成，共生成 {len(lesson_files)} 个教案文件")
        if lesson_files:
            print(f"  教案保存目录: {config.LESSONS_DIR}")
    except Exception as e:
        print(f"✗ 生成教案失败: {str(e)}")
        return
    
    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='AI学习方案生成系统')
    
    # 添加子命令支持
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 生成学习方案命令
    plan_parser = subparsers.add_parser('plan', help='生成学习方案')
    plan_parser.add_argument('profile', help='用户画像YAML文件路径')
    plan_parser.add_argument('-o', '--output', help='输出文件路径（可选）')
    plan_parser.add_argument('-f', '--format', choices=['json', 'yaml'], default='json',
                            help='输出格式（默认：json）')
    plan_parser.add_argument('-g', '--generate-lessons', action='store_true',
                            help='生成知识点教案（默认不生成）')
    
    # 从学习方案生成教案命令
    lesson_parser = subparsers.add_parser('lessons', help='基于已有学习方案生成教案')
    lesson_parser.add_argument('plan', help='学习方案文件路径（JSON或YAML）')
    lesson_parser.add_argument('-p', '--profile', help='用户画像YAML文件路径（可选，用于更准确的个性化）')
    
    # 快速测试知识点生成命令
    points_parser = subparsers.add_parser('points', help='快速测试知识点生成（不进行依赖分析和排序）')
    points_parser.add_argument('-p', '--profile', help='用户画像YAML文件路径（可选，如果不提供则使用--goal）')
    points_parser.add_argument('-g', '--goal', help='学习目标（如果不提供--profile则必须提供）')
    points_parser.add_argument('-o', '--output', help='输出JSON文件路径（可选）')
    
    args = parser.parse_args()
    
    # 根据命令执行相应功能
    if args.command == 'plan':
        # 检查文件是否存在
        profile_path = Path(args.profile)
        if not profile_path.exists():
            print(f"错误：用户画像文件不存在: {args.profile}")
            return
        generate_learning_plan(str(profile_path), args.output, args.format, args.generate_lessons)
    
    elif args.command == 'lessons':
        # 检查文件是否存在
        plan_path = Path(args.plan)
        if not plan_path.exists():
            print(f"错误：学习方案文件不存在: {args.plan}")
            return
        
        profile_path = None
        if args.profile:
            profile_path_obj = Path(args.profile)
            if not profile_path_obj.exists():
                print(f"警告：用户画像文件不存在: {args.profile}，将使用学习方案中的信息")
            else:
                profile_path = str(profile_path_obj)
        
        generate_lessons_from_plan(str(plan_path), profile_path)
    
    elif args.command == 'points':
        # 测试知识点生成
        profile_path = None
        if args.profile:
            profile_path_obj = Path(args.profile)
            if not profile_path_obj.exists():
                print(f"错误：用户画像文件不存在: {args.profile}")
                return
            profile_path = str(profile_path_obj)
        
        test_knowledge_points(profile_path, args.goal, args.output)
    
    else:
        # 如果没有指定命令，显示帮助信息
        parser.print_help()


if __name__ == '__main__':
    main()
