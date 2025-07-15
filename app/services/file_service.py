import os
import zipfile
from flask import current_app

def allowed_file(filename):
    """检查文件是否为允许的类型"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def extract_zip(zip_path, extract_dir):
    """解压ZIP文件到指定目录"""
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    return extract_dir

def get_file_paths(directory):
    """获取目录中所有文件的路径"""
    file_paths = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            file_paths.append(file_path)
    return file_paths

def group_files_by_type(file_paths):
    """按文件类型对文件进行分组"""
    pdf_files = []
    xml_files = []
    other_files = []
    
    for file_path in file_paths:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.pdf':
            pdf_files.append(file_path)
        elif ext == '.xml':
            xml_files.append(file_path)
        else:
            other_files.append(file_path)
    
    return {
        'pdf': pdf_files,
        'xml': xml_files,
        'other': other_files
    } 