import os
import json
from dotenv import load_dotenv

# 加载.env文件中的环境变量（如果存在）
load_dotenv()


def _json_env(name, default):
    value = os.environ.get(name)
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


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
    GLOBAL_STATS_FILE = os.environ.get('GLOBAL_STATS_FILE') or os.path.join(DATA_FOLDER, 'global_stats.json')
    
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

    # DingTalk auth. Keep secrets in .env only.
    DINGTALK_AUTH_ENABLED = os.environ.get('DINGTALK_AUTH_ENABLED', 'false').lower() in {'1', 'true', 'yes', 'on'}
    DINGTALK_AUTH_FLOW = (os.environ.get('DINGTALK_AUTH_FLOW') or 'oauth2').strip().lower()
    DINGTALK_CLIENT_ID = (os.environ.get('DINGTALK_CLIENT_ID') or '').strip()
    DINGTALK_CLIENT_SECRET = (os.environ.get('DINGTALK_CLIENT_SECRET') or '').strip()
    DINGTALK_REDIRECT_URI = (os.environ.get('DINGTALK_REDIRECT_URI') or '').strip()
    DINGTALK_SCOPE = (os.environ.get('DINGTALK_SCOPE') or 'openid').strip()
    DINGTALK_AGENT_ID = int(os.environ.get('DINGTALK_AGENT_ID') or '0')
    DINGTALK_DEFAULT_ORIGINATOR_USER_ID = (os.environ.get('DINGTALK_DEFAULT_ORIGINATOR_USER_ID') or '').strip()

    # Travel reimbursement approval template. The field map keys are internal summary keys,
    # and values must match DingTalk approval component names exactly.
    DINGTALK_TRAVEL_PROCESS_CODE = (os.environ.get('DINGTALK_TRAVEL_PROCESS_CODE') or '').strip()
    DINGTALK_TRAVEL_DEPT_ID = int(os.environ.get('DINGTALK_TRAVEL_DEPT_ID') or '-1')
    DINGTALK_TRAVEL_FIELD_MAP = _json_env('DINGTALK_TRAVEL_FIELD_MAP', {})

    # Hosts that should always require DingTalk login, useful when public access comes through TCP stream.
    # Example: work.bdcatek.com:12306
    DINGTALK_AUTH_PUBLIC_HOSTS = {
        host.strip().lower()
        for host in (os.environ.get('DINGTALK_AUTH_PUBLIC_HOSTS') or '').split(',')
        if host.strip()
    }

    INTERNAL_CIDRS = [
        cidr.strip()
        for cidr in (os.environ.get('INTERNAL_CIDRS') or '127.0.0.0/8,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16').split(',')
        if cidr.strip()
    ]
