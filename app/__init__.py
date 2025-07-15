import os
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
    
    # 注册蓝图
    from app.routes import main_bp
    app.register_blueprint(main_bp)
    
    return app 