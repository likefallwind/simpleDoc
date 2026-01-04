# AI学习方案生成系统

根据用户画像和学习目标，自动生成包含知识点序列的培养方案。

## 功能特性

1. **课程知识点管理**：自动提取或从MD文件读取课程知识点
2. **前置依赖分析**：智能分析知识点之间的依赖关系
3. **学习路径排序**：基于依赖关系、难度等因素生成最优学习顺序
4. **用户画像支持**：根据用户背景定制化学习方案

## 安装

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 配置API密钥：
   - 复制 `config.example.py` 为 `config.py`
   - 在 `config.py` 中填写您的 ModelScope API 密钥

## 使用方法

### 1. 准备用户画像文件

创建YAML格式的用户画像文件，例如 `data/profiles/my_profile.yaml`：

```yaml
user:
  name: "学生姓名"
  background:
    courses:
      - "Python基础"
      - "数据结构与算法"
  learning_goal: "强化学习"
```

**注意**：用户画像中只需要列出学过的课程，系统会自动从课程知识点文档中提取已掌握的知识点。如果某个课程的知识点文档不存在，系统会自动使用LLM生成。

### 2. 运行程序

```bash
# 基本用法（自动保存到 data/profiles/ 目录，同时输出到控制台）
python main.py data/profiles/my_profile.yaml

# 指定输出文件路径（同时输出到控制台和文件）
python main.py data/profiles/my_profile.yaml -o my_plan.json

# 输出为YAML格式
python main.py data/profiles/my_profile.yaml -o my_plan.yaml -f yaml
```

**注意**：
- 如果不指定 `-o` 参数，系统会自动生成文件名并保存到 `data/profiles/` 目录
- 文件名格式：`用户名_学习目标_时间戳.格式`（例如：`示例学生_强化学习_20240104_160000.json`）
- 无论是否指定输出文件，结果都会同时显示在控制台和保存到文件

## 输出格式

培养方案包含以下信息：

- **user**: 用户信息
- **course**: 课程信息
- **learning_path**: 排序后的知识点列表（包含学习顺序）
- **dependencies**: 知识点依赖关系
- **statistics**: 统计信息

## 工作流程

1. 加载用户画像
2. 获取或生成课程知识点（如果MD文件不存在，会调用LLM生成）
3. 分析每个知识点的前置依赖
4. 对所有知识点进行排序（调用LLM 3次取平均值）
5. 生成并输出培养方案

## 配置说明

在 `config.py` 中可以配置：

- `MAX_KNOWLEDGE_POINTS`: 知识点数量上限（默认100）
- `SORT_RETRY_COUNT`: 排序时调用LLM的次数（默认3次）

## 文件结构

```
simpleDoc/
├── main.py                    # 主程序入口
├── user_profile.py           # 用户画像解析
├── course_knowledge.py       # 课程知识点管理
├── prerequisite_analyzer.py  # 前置依赖分析
├── learning_path.py          # 学习路径排序
├── llm_service.py           # LLM服务封装
├── config.py                # 配置文件（需自行填写API密钥）
├── config.example.py         # 配置文件模板
├── prompts.py               # 提示词模板
├── data/
│   ├── courses/             # 课程知识点MD文件存储目录
│   └── profiles/            # 用户画像YAML文件
└── requirements.txt         # 依赖包
```

## 注意事项

1. **API密钥安全**：`config.py` 包含API密钥，不会被提交到版本控制（已在.gitignore中）
2. **知识点数量限制**：如果知识点超过100个，会自动截断
3. **排序稳定性**：系统会调用LLM 3次进行排序，取平均值以提高稳定性
4. **循环依赖**：系统会自动检测循环依赖，并在排序时处理

## 示例

查看 `data/profiles/example_profile.yaml` 了解用户画像格式示例。
