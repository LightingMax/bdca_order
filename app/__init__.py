import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from flask_cors import CORS
from app.config import Config

def create_app(config_class=Config):
    # 创建Flask应用
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # 启用CORS
    CORS(app)
    
    # 确保必要的目录存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['TEMP_FOLDER'], exist_ok=True)
    os.makedirs(app.config['DATA_FOLDER'], exist_ok=True)
    os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
    os.makedirs(app.config['LOG_FOLDER'], exist_ok=True)
    
    # 配置日志
    setup_logging(app)
    
    # 注册蓝图
    from app.routes import main_bp
    app.register_blueprint(main_bp)
    
    app.logger.info('应用启动成功')
    
    return app

def setup_logging(app):
    """配置应用日志"""
    log_level = logging.DEBUG if app.config['DEBUG'] else logging.INFO
    
    # 创建日志格式
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s [in %(pathname)s:%(lineno)d]'
    )
    
    # 文件处理器 - 主日志文件
    file_handler = RotatingFileHandler(
        os.path.join(app.config['LOG_FOLDER'], 'app.log'),
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)
    
    # 文件处理器 - 错误日志文件
    error_file_handler = RotatingFileHandler(
        os.path.join(app.config['LOG_FOLDER'], 'error.log'),
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    error_file_handler.setFormatter(formatter)
    error_file_handler.setLevel(logging.ERROR)
    
    # 添加处理器到应用日志
    app.logger.addHandler(file_handler)
    app.logger.addHandler(error_file_handler)
    app.logger.setLevel(log_level)
    
    # 设置Werkzeug日志
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_handler = RotatingFileHandler(
        os.path.join(app.config['LOG_FOLDER'], 'access.log'),
        maxBytes=10485760,
        backupCount=5
    )
    werkzeug_handler.setFormatter(formatter)
    werkzeug_logger.addHandler(werkzeug_handler)
    werkzeug_logger.setLevel(log_level) 