# ModelScope API配置
MODELSCOPE_BASE_URL = 'https://api-inference.modelscope.cn/v1'
MODELSCOPE_API_KEY = 'YOUR_API_KEY_HERE'  # 请替换为您的ModelScope Token
MODELSCOPE_MODEL = 'deepseek-ai/DeepSeek-V3.2'

# 知识点配置
MAX_KNOWLEDGE_POINTS = 100  # 知识点数量上限

# 排序稳定性配置
SORT_RETRY_COUNT = 3  # 排序时调用LLM的次数，取平均值

# 数据目录配置
DATA_DIR = 'data'
COURSES_DIR = 'data/courses'
PROFILES_DIR = 'data/profiles'
