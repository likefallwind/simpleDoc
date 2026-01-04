"""
提示词模板模块
定义各种LLM提示词模板
"""
from typing import List, Dict


def get_knowledge_points_extraction_prompt(learning_goal: str, course_name: str = None) -> str:
    """
    获取知识点提取提示词
    
    Args:
        learning_goal: 学习目标
        course_name: 课程名称（可选）
    
    Returns:
        提示词字符串
    """
    course_part = f"课程名称：{course_name}\n" if course_name else ""
    
    prompt = f"""你是一位教育专家，擅长分析学习目标并提取知识点。

请根据以下学习目标，提取出需要学习的知识点列表。

{course_part}学习目标：{learning_goal}

要求：
1. 提取的知识点应该具体、明确，粒度适中（不要太细也不要太粗）
2. 每个知识点应该是一个独立的学习单元
3. 知识点数量应该合理（建议5-20个）
4. 知识点应该覆盖学习目标的核心内容

请以JSON格式输出，格式如下：
{{
    "course_name": "课程名称",
    "course_description": "课程描述",
    "knowledge_points": [
        {{
            "name": "知识点名称",
            "description": "知识点描述"
        }}
    ]
}}

请直接输出JSON，不要包含其他文字说明。"""
    
    return prompt


def get_prerequisite_analysis_prompt_batch(knowledge_points: List[Dict], 
                                           user_background: Dict = None) -> str:
    """
    批量获取前置依赖分析提示词
    
    Args:
        knowledge_points: 知识点列表，每个元素包含name和description
        user_background: 用户背景信息（可选）
    
    Returns:
        提示词字符串
    """
    # 构建知识点列表文本
    points_text = "需要分析的知识点列表：\n"
    for i, point in enumerate(knowledge_points, 1):
        name = point.get('name', '')
        desc = point.get('description', '')
        points_text += f"{i}. {name}"
        if desc:
            points_text += f"：{desc}"
        points_text += "\n"
    
    background_part = ""
    if user_background:
        courses = user_background.get('courses', [])
        knowledge_points_bg = user_background.get('knowledge_points', [])
        
        if courses or knowledge_points_bg:
            background_part = "\n用户已掌握的内容：\n"
            if courses:
                background_part += f"已学课程：{', '.join(courses)}\n"
            if knowledge_points_bg:
                background_part += f"已掌握知识点：{', '.join(knowledge_points_bg)}\n"
    
    prompt = f"""你是一位教育专家，擅长分析知识点之间的依赖关系。

请分析以下知识点列表，判断学习每个知识点需要哪些前置知识点。

{points_text}{background_part}

重要要求：
1. **知识点颗粒度要求**：前置知识点的颗粒度应该与课程知识点对齐。参考标准：
   - 课程知识点通常是较大的概念单元（如"Python基本语法与编码规范"、"马尔可夫决策过程（MDP）"）
   - 不要生成过于细粒度的知识点（如"python特定函数用法"、"PyTorch某个具体函数调用方法"等过于细粒度的基础概念）
   - 前置知识点应该是比课程低一级别的知识点，比如一个课程可能由10几个知识点构成
2. 前置知识点应该是用户必须学习且可能不知道的（如果用户已掌握，则不需要列出）
3. 只列出真正必要的前置知识点，避免过度细化
4. 如果某个知识点不需要前置知识点，返回空列表

请以JSON格式输出，格式如下：
{{
    "results": [
        {{
            "knowledge_point": "知识点名称",
            "prerequisites": [
                {{
                    "name": "前置知识点名称",
                    "description": "前置知识点描述（可选）",
                    "reason": "为什么需要这个前置知识点"
                }}
            ]
        }}
    ]
}}

请直接输出JSON，不要包含其他文字说明。"""
    
    return prompt


def get_learning_path_sorting_prompt(knowledge_points: List[Dict], 
                                     dependencies: Dict[str, List[str]] = None,
                                     user_background: Dict = None) -> str:
    """
    获取学习路径排序提示词
    
    Args:
        knowledge_points: 知识点列表，每个元素包含name和description
        dependencies: 依赖关系字典，key为知识点名称，value为前置知识点列表
        user_background: 用户背景信息（可选）
    
    Returns:
        提示词字符串
    """
    # 构建知识点列表文本
    points_text = "知识点列表：\n"
    for i, point in enumerate(knowledge_points, 1):
        name = point.get('name', '')
        desc = point.get('description', '')
        points_text += f"{i}. {name}"
        if desc:
            points_text += f"：{desc}"
        points_text += "\n"
    
    # 构建依赖关系文本
    deps_text = ""
    if dependencies:
        deps_text = "\n知识点依赖关系：\n"
        for point, prereqs in dependencies.items():
            if prereqs:
                deps_text += f"- {point} 需要先学习：{', '.join(prereqs)}\n"
    
    # 构建用户背景文本
    background_text = ""
    if user_background:
        courses = user_background.get('courses', [])
        knowledge_points_bg = user_background.get('knowledge_points', [])
        
        if courses or knowledge_points_bg:
            background_text = "\n用户背景：\n"
            if courses:
                background_text += f"已学课程：{', '.join(courses)}\n"
            if knowledge_points_bg:
                background_text += f"已掌握知识点：{', '.join(knowledge_points_bg)}\n"
    
    prompt = f"""你是一位教育专家，擅长设计学习路径。

请根据以下知识点列表和依赖关系，按照学习顺序对所有知识点进行排序。

{points_text}{deps_text}{background_text}

要求：
1. 考虑知识点之间的依赖关系（前置知识点必须排在后面）
2. 考虑知识点的难度（从易到难）
3. 考虑知识点的重要性（重要的基础知识点优先）
4. 确保学习路径合理、连贯
5. 如果存在循环依赖，请根据实际情况合理排序

请以JSON格式输出排序后的知识点列表，格式如下：
{{
    "sorted_knowledge_points": [
        {{
            "name": "知识点名称",
            "description": "知识点描述",
            "order": 1
        }}
    ]
}}

请直接输出JSON，不要包含其他文字说明。"""
    
    return prompt
