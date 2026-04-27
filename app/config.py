import os
from dotenv import load_dotenv

# 加载.env文件中的环境变量（如果存在）
load_dotenv()

class Config:
    # Flask配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-for-order-reimbursement'
    
    # 文件路径配置
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, os.pardir))
    
    UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, 'app', 'static', 'uploads')
    TEMP_FOLDER = os.path.join(PROJECT_ROOT, 'temp')
    DATA_FOLDER = os.path.join(PROJECT_ROOT, 'data')
    OUTPUT_FOLDER = os.path.join(PROJECT_ROOT, 'app', 'static', 'output')
    LOG_FOLDER = os.path.join(PROJECT_ROOT, 'logs')
    
    # 用户数据文件
    USER_DATA_FILE = os.path.join(DATA_FOLDER, 'user_data.json')
    
    # 允许上传的文件类型（智能处理）
    ALLOWED_EXTENSIONS = {'zip', 'pdf'}
    
    # 最大上传文件大小 (50MB)
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024
    
    # 上传优化配置
    UPLOAD_CHUNK_SIZE = 8192  # 8KB块大小
    UPLOAD_TIMEOUT = 300  # 5分钟超时
    
    # 默认打印机配置（仅来自环境变量；须与 CUPS 队列名完全一致）
    DEFAULT_PRINTER_NAME = (os.environ.get('DEFAULT_PRINTER_NAME') or '').strip()
    DEFAULT_MEDIA_SOURCE = (os.environ.get('DEFAULT_MEDIA_SOURCE') or 'auto').strip()
    
    # 通义千问API配置
    QWEN_API_BASE_URL = os.environ.get('QWEN_API_BASE_URL') or 'https://dashscope.aliyuncs.com/compatible-mode/v1'
    QWEN_API_KEY = os.environ.get('QWEN_API_KEY') or 'sk-4b678a7de6d34b878356518397592170'
    QWEN_MODEL = os.environ.get('QWEN_MODEL') or 'qwen2.5-32b-instruct'
    QWEN_API_TIMEOUT = int(os.environ.get('QWEN_API_TIMEOUT', 180)) 