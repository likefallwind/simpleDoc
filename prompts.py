"""
提示词模板模块
定义各种LLM提示词模板
"""
from typing import List, Dict


def get_knowledge_points_extraction_prompt(learning_goal: str, course_name: str = None) -> str:
    """
    获取知识点提取提示词
    """
    course_part = f"课程名称：{course_name}\n" if course_name else ""
    
    prompt = f"""你是一位资深的大学课程设计专家。你的任务是为以下学习目标设计一份标准教科书级别的教学大纲。

{course_part}学习目标：{learning_goal}

请提取核心知识点，并严格遵守以下**粒度控制标准**：

1.  **粒度锚点**：请将其视为一本标准大学教材的**“章（Chapter）”**或**“核心小节（Key Section）”**标题。
2.  **拒绝微观细节**：不要列出具体的API函数名、单一的公式或过于琐碎的操作步骤（如“如何安装软件”、“print函数的用法”）。
3.  **独立性**：每个知识点应该是一个可以独立用1-2小时讲授的概念单元。
4.  **数量控制**：保持在 8-15 个核心知识点之间，确保覆盖全貌但不过于发散。

示例（正确 vs 错误）：
- [正确] 线性回归模型
- [错误] 机器学习介绍 (太宽泛)
- [错误] 均方误差公式的推导过程 (太细，这是线性回归内部的细节)
- [错误] sklearn库的安装 (太琐碎)

请以JSON格式输出：
{{
    "course_name": "课程名称",
    "course_description": "20字以内的简短描述",
    "knowledge_points": [
        {{
            "name": "知识点名称",
            "description": "简要描述该知识点包含的核心概念"
        }}
    ]
}}
请直接输出JSON。"""
    
    return prompt


def get_prerequisite_analysis_prompt_batch(knowledge_points: List[Dict], 
                                           user_background: Dict = None) -> str:
    """
    批量获取前置依赖分析提示词 (优化版：增加区分内部细节与外部依赖)
    """
    points_text = "需要分析的知识点列表：\n"
    for i, point in enumerate(knowledge_points, 1):
        name = point.get('name', '')
        desc = point.get('description', '')
        points_text += f"{i}. {name} ({desc})\n"
    
    background_part = ""
    if user_background and (user_background.get('courses') or user_background.get('knowledge_points')):
        background_part = "\n用户已掌握（无需列为前置）：\n"
        if user_background.get('courses'):
            background_part += f"已学课程：{', '.join(user_background['courses'])}\n"
    
    prompt = f"""你是一位认知心理学和教育学专家。请分析以下知识点，找出学习它们必须先掌握的**外部前置依赖**。

{points_text}{background_part}

**核心原则（粒度控制）：**
1.  **区分"前置依赖"与"子概念"**：
    * [前置依赖] 是**学习A之前必须已经学会的B**（通常来自其他学科或基础课程）。
    * [子概念] 是**在学习A的过程中会学到的细节**（不要列为前置！）。
    * *例子*：学习"神经网络"时，"矩阵乘法"是前置依赖（需要先会）；但"激活函数"是神经网络的内部子概念（不用先会，课上会讲），**不要**列为前置。

2.  **粒度对齐**：前置知识点的粒度应与目标知识点保持一致（即"章"或"核心概念"级别），不要下钻到微观定义。
    * *例子*：如果目标是"动态规划"，前置应该是"递归思想"（概念级），而不是"斐波那契数列的具体代码"（细节级）。

3.  **只返回知识点，不要返回课程名称**：
    * **重要**：前置依赖必须是具体的知识点，不能是整个课程的名称。
    * 如果某个前置依赖是某个课程的内容，请返回该课程中的具体知识点，而不是课程名称。
    * *错误示例*：返回"线性代数基础"、"概率论基础"、"微积分基础"等课程名称作为前置依赖
    * *正确示例*：
      - 如果依赖线性代数，应返回"矩阵运算"、"向量空间"、"线性变换"等具体知识点
      - 如果依赖概率论，应返回"条件概率"、"随机变量"、"期望与方差"等具体知识点
      - 如果依赖微积分，应返回"导数与梯度"、"积分"、"链式法则"等具体知识点
    * 如果用户已学过的课程中包含了相关知识点（见上面的"用户已掌握"部分），则无需列出。

4.  **仅列出必要项**：如果某知识点是零基础可学的（如"Python变量定义"），则前置列表为空。

请以JSON格式输出：
{{
    "results": [
        {{
            "knowledge_point": "输入列表中的知识点名称",
            "prerequisites": [
                {{
                    "name": "前置知识点名称",
                    "reason": "必须简短说明为什么这是前置条件（例如：计算梯度需要用到导数）"
                }}
            ]
        }}
    ]
}}
请直接输出JSON。"""
    
    return prompt

# get_learning_path_sorting_prompt 函数保持不变或做微调即可
def get_learning_path_sorting_prompt(knowledge_points: List[Dict], 
                                     dependencies: Dict[str, List[str]] = None,
                                     user_background: Dict = None) -> str:
    # ... (保持你原有的逻辑，这个部分通常问题不大)
    # 为了完整性，可以复制原有的代码，这里省略以节省篇幅
    # ...
    # 原代码的 get_learning_path_sorting_prompt 实现
    points_text = "知识点列表：\n"
    for i, point in enumerate(knowledge_points, 1):
        name = point.get('name', '')
        points_text += f"{i}. {name}\n"
    
    deps_text = ""
    if dependencies:
        deps_text = "\n必须遵守的依赖关系（前置 -> 后续）：\n"
        for point, prereqs in dependencies.items():
            if prereqs:
                for req in prereqs:
                     deps_text += f"- 先学 [{req}]，再学 [{point}]\n"
    
    prompt = f"""你是一位课程编排专家。请根据依赖关系对知识点进行教学排序。

{points_text}{deps_text}

要求：
1. **绝对遵守依赖关系**：如果 A 依赖 B，B 必须排在 A 前面。
2. **由浅入深**：基础概念在前，高级应用在后。
3. **输出完整**：必须包含列表中的所有知识点，不能遗漏。

请以JSON输出：
{{
    "sorted_knowledge_points": [
        {{
            "name": "知识点名称",
            "order": 1,
            "reason": "排序理由"
        }}
    ]
}}
"""
    return prompt


def get_lesson_generation_prompt(knowledge_point: Dict, related_info: Dict,
                                user_background: Dict, learning_goal: str) -> str:
    """
    获取教案生成提示词
    
    Args:
        knowledge_point: 知识点字典，包含name和description
        related_info: 相关知识点信息（前置、后续、位置等）
        user_background: 用户背景信息
        learning_goal: 学习目标
    
    Returns:
        提示词字符串
    """
    point_name = knowledge_point.get('name', '')
    point_desc = knowledge_point.get('description', '')
    
    # 构建知识点信息
    point_info = f"知识点名称：{point_name}"
    if point_desc:
        point_info += f"\n知识点描述：{point_desc}"
    
    # 构建学习路径信息
    order = related_info.get('order')
    total = related_info.get('total')
    path_info = ""
    if order and total:
        path_info = f"\n\n学习路径位置：第 {order}/{total} 个知识点"
    
    # 构建前置知识点信息
    prerequisites = related_info.get('prerequisites', [])
    prereq_info = ""
    if prerequisites:
        prereq_info = f"\n\n前置知识点：\n"
        for i, prereq in enumerate(prerequisites, 1):
            prereq_info += f"{i}. {prereq}\n"
    else:
        prereq_info = "\n\n前置知识点：无（这是基础知识点）"
    
    # 构建后续知识点信息
    subsequent = related_info.get('subsequent_points', [])
    subsequent_info = ""
    if subsequent:
        subsequent_info = f"\n\n后续知识点（依赖此知识点）：\n"
        for i, sub in enumerate(subsequent, 1):
            subsequent_info += f"{i}. {sub}\n"
    
    # 构建相邻知识点信息
    prev_point = related_info.get('prev_point')
    next_point = related_info.get('next_point')
    neighbor_info = ""
    if prev_point or next_point:
        neighbor_info = "\n\n相邻知识点：\n"
        if prev_point:
            neighbor_info += f"- 上一个知识点：{prev_point}\n"
        if next_point:
            neighbor_info += f"- 下一个知识点：{next_point}\n"
    
    # 构建用户背景信息
    background_info = ""
    if user_background:
        courses = user_background.get('courses', [])
        knowledge_points = user_background.get('knowledge_points', [])
        
        if courses or knowledge_points:
            background_info = "\n\n用户背景：\n"
            if courses:
                background_info += f"已学课程：{', '.join(courses)}\n"
            if knowledge_points:
                background_info += f"已掌握知识点：{', '.join(knowledge_points[:10])}"
                if len(knowledge_points) > 10:
                    background_info += f"（共{len(knowledge_points)}个）\n"
                else:
                    background_info += "\n"
    
    prompt = f"""你是一位经验丰富的教育专家，擅长编写个性化教案。

请为以下知识点生成一份详细的教学教案。

{point_info}{path_info}{prereq_info}{subsequent_info}{neighbor_info}{background_info}

学习目标：{learning_goal}

教案要求：
1. **个性化定制**：根据用户已学课程和已掌握知识点，调整教学内容的深度和广度
   - 如果用户已经掌握相关前置知识，可以适当加快节奏或深入讲解
   - 如果用户是初学者，需要更详细的解释和更多示例
2. **知识点关联**：
   - 明确说明与前置知识点的关系，帮助用户建立知识连接
   - 提及后续知识点，让用户了解学习此知识点的意义
   - 利用相邻知识点，帮助用户理解学习顺序
3. **内容结构**：教案应包含以下部分（使用Markdown格式）：
   - 标题：知识点名称
   - 学习目标：明确说明学完此知识点后应掌握的内容
   - 前置知识回顾：简要回顾相关前置知识点（如果用户已掌握，可以简化）
   - 核心内容：详细讲解知识点的主要内容
   - 重点难点：突出重要的概念和可能遇到的难点
   - 实例讲解：提供具体的例子帮助理解
   - 实践练习：提供练习题或实践任务
   - 知识拓展：介绍与此知识点相关的扩展内容
   - 总结：总结关键要点
   - 下一步学习：提示下一个要学习的知识点
4. **教学风格**：
   - 语言清晰、易懂
   - 循序渐进，由浅入深
   - 结合实际应用场景
   - 考虑用户的学习背景，使用合适的术语和例子

请直接输出完整的Markdown格式教案，不要包含其他说明文字。"""
    
    return prompt
