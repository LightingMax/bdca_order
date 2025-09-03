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
    
    # 允许上传的文件类型
    ALLOWED_EXTENSIONS = {'zip'}
    
    # 最大上传文件大小 (50MB)
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024
    
    # 上传优化配置
    UPLOAD_CHUNK_SIZE = 8192  # 8KB块大小
    UPLOAD_TIMEOUT = 300  # 5分钟超时
    
    # 打印API服务配置
    PRINT_API_BASE_URL = os.environ.get('PRINT_API_BASE_URL') or 'http://localhost:12346'
    PRINT_API_TOKEN = os.environ.get('PRINT_API_TOKEN') or 'TOKEN_PRINT_API_KEY_9527'
    PRINT_API_TIMEOUT = int(os.environ.get('PRINT_API_TIMEOUT', 30))
    
    # 默认打印机配置
    DEFAULT_PRINTER_NAME = os.environ.get('DEFAULT_PRINTER_NAME') or 'HP-LaserJet-MFP-M437-M443'
    
    # 打印API端点
    PRINT_API_ENDPOINTS = {
        'printers': '/printers',
        'default_printer': '/default-printer',
        'print': '/print',
        'health': '/health'
    } 