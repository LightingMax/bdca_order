import os
import zipfile
from flask import current_app

def allowed_file(filename):
    """检查文件是否为允许的类型"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def extract_zip(zip_path, extract_dir):
    """解压ZIP文件到指定目录，支持中文编码"""
    logger = current_app.logger
    logger.info(f"开始解压文件: {zip_path} 到 {extract_dir}")
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # 获取所有文件名列表
            name_list = zip_ref.namelist()
            logger.info(f"ZIP文件中包含 {len(name_list)} 个文件")
            
            # 遍历处理每个文件
            for file_name in name_list:
                try:
                    # 尝试使用不同编码解码文件名
                    encodings = ['utf-8', 'gbk', 'gb2312', 'cp437']
                    decoded_name = None
                    
                    for encoding in encodings:
                        try:
                            # 尝试解码文件名
                            decoded_name = file_name.encode('cp437').decode(encoding)
                            logger.debug(f"成功使用 {encoding} 解码文件名: {decoded_name}")
                            break
                        except UnicodeDecodeError:
                            continue
                    
                    # 如果所有编码都失败，使用原始名称
                    if decoded_name is None:
                        decoded_name = file_name
                        logger.warning(f"无法解码文件名，使用原始名称: {file_name}")
                    
                    # 提取文件
                    data = zip_ref.read(file_name)
                    target_path = os.path.join(extract_dir, decoded_name)
                    
                    # 确保目标目录存在
                    target_dir = os.path.dirname(target_path)
                    if not os.path.exists(target_dir) and target_dir:
                        os.makedirs(target_dir, exist_ok=True)
                    
                    # 写入文件
                    with open(target_path, 'wb') as f:
                        f.write(data)
                    
                    logger.debug(f"成功解压文件: {decoded_name}")
                        
                except Exception as e:
                    logger.error(f"解压文件 {file_name} 时出错: {str(e)}")
                    # 如果单个文件解压失败，继续处理其他文件
                    continue
        
        logger.info(f"文件解压完成，共处理 {len(name_list)} 个文件")
    except Exception as e:
        logger.error(f"解压ZIP文件时发生错误: {str(e)}")
        raise
    
    return extract_dir

def get_file_paths(directory):
    """获取目录中所有文件的路径"""
    file_paths = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            file_paths.append(file_path)
    
    current_app.logger.info(f"在目录 {directory} 中找到 {len(file_paths)} 个文件")
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
    
    current_app.logger.info(f"文件分组结果: PDF={len(pdf_files)}个, XML={len(xml_files)}个, 其他={len(other_files)}个")
    
    return {
        'pdf': pdf_files,
        'xml': xml_files,
        'other': other_files
    } 