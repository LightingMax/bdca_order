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