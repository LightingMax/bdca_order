import os
import zipfile
import hashlib
import json
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

def calculate_file_hash(file_path):
    """计算文件的SHA-256哈希值"""
    logger = current_app.logger
    logger.debug(f"计算文件哈希: {file_path}")
    
    hash_sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        # 每次读取4MB数据进行哈希计算，避免一次性读取大文件
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b''):
            hash_sha256.update(chunk)
    
    file_hash = hash_sha256.hexdigest()
    logger.debug(f"文件哈希值: {file_hash}")
    return file_hash

def save_file_hash(file_hash, file_info):
    """保存文件哈希记录"""
    logger = current_app.logger
    hash_file = os.path.join(current_app.config['DATA_FOLDER'], 'file_hashes.json')
    
    # 加载现有哈希记录
    hashes = {}
    if os.path.exists(hash_file):
        try:
            with open(hash_file, 'r', encoding='utf-8') as f:
                hashes = json.load(f)
        except Exception as e:
            logger.error(f"读取哈希记录文件出错: {str(e)}")
    
    # 添加新记录
    hashes[file_hash] = file_info
    
    # 保存更新后的记录
    try:
        with open(hash_file, 'w', encoding='utf-8') as f:
            json.dump(hashes, f, ensure_ascii=False, indent=2)
        logger.info(f"文件哈希记录已保存: {file_hash}")
    except Exception as e:
        logger.error(f"保存哈希记录文件出错: {str(e)}")

def check_file_exists(file_hash):
    """检查文件是否已上传过（通过哈希值）"""
    logger = current_app.logger
    hash_file = os.path.join(current_app.config['DATA_FOLDER'], 'file_hashes.json')
    
    # 如果哈希记录文件不存在，说明没有上传过任何文件
    if not os.path.exists(hash_file):
        logger.debug("哈希记录文件不存在，文件未上传过")
        return None
    
    # 加载哈希记录
    try:
        with open(hash_file, 'r', encoding='utf-8') as f:
            hashes = json.load(f)
    except Exception as e:
        logger.error(f"读取哈希记录文件出错: {str(e)}")
        return None
    
    # 检查哈希值是否存在
    if file_hash in hashes:
        logger.info(f"文件已上传过: {file_hash}")
        return hashes[file_hash]
    else:
        logger.debug(f"文件未上传过: {file_hash}")
        return None 

def check_order_processed(order_id):
    """检查订单是否已处理过"""
    logger = current_app.logger
    hash_file = os.path.join(current_app.config['DATA_FOLDER'], 'file_hashes.json')
    
    # 如果哈希记录文件不存在，说明没有处理过任何订单
    if not os.path.exists(hash_file):
        logger.debug(f"哈希记录文件不存在，订单 {order_id} 未处理过")
        return False
    
    # 加载哈希记录
    try:
        with open(hash_file, 'r', encoding='utf-8') as f:
            hashes = json.load(f)
    except Exception as e:
        logger.error(f"读取哈希记录文件出错: {str(e)}")
        return False
    
    # 遍历所有文件记录，检查是否存在该订单ID
    for file_hash, file_info in hashes.items():
        if 'results' in file_info:
            for result in file_info['results']:
                if result.get('order_id') == order_id:
                    logger.info(f"订单 {order_id} 已处理过，在文件 {file_info.get('filename', '未知')} 中")
                    return True
    
    logger.debug(f"订单 {order_id} 未处理过")
    return False

def get_processed_orders():
    """获取所有已处理过的订单ID列表"""
    logger = current_app.logger
    hash_file = os.path.join(current_app.config['DATA_FOLDER'], 'file_hashes.json')
    
    # 如果哈希记录文件不存在，返回空列表
    if not os.path.exists(hash_file):
        logger.debug("哈希记录文件不存在，返回空订单列表")
        return []
    
    # 加载哈希记录
    try:
        with open(hash_file, 'r', encoding='utf-8') as f:
            hashes = json.load(f)
    except Exception as e:
        logger.error(f"读取哈希记录文件出错: {str(e)}")
        return []
    
    # 收集所有订单ID
    processed_orders = set()
    for file_hash, file_info in hashes.items():
        if 'results' in file_info:
            for result in file_info['results']:
                if 'order_id' in result:
                    processed_orders.add(result['order_id'])
    
    logger.info(f"找到 {len(processed_orders)} 个已处理过的订单")
    return list(processed_orders) 