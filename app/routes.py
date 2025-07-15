import os
import uuid
from flask import Blueprint, render_template, request, jsonify, current_app, send_from_directory
from werkzeug.utils import secure_filename

from app.services.file_service import allowed_file, extract_zip
from app.services.pdf_service import process_pdf_files
from app.services.print_service import print_pdf
from app.services.user_service import get_user_mac, save_user_data, get_all_user_stats

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """渲染主页"""
    current_app.logger.debug("访问主页")
    return render_template('index.html')

@main_bp.route('/statistics')
def statistics():
    """渲染统计页面"""
    current_app.logger.debug("访问统计页面")
    return render_template('statistics.html')

@main_bp.route('/api/upload', methods=['POST'])
def upload_file():
    """处理文件上传"""
    logger = current_app.logger
    logger.info("收到文件上传请求")
    
    # 检查是否有文件
    if 'files' not in request.files:
        logger.warning("上传请求中没有文件")
        return jsonify({'error': '没有文件'}), 400
    
    files = request.files.getlist('files')
    
    # 检查是否有文件被选择
    if len(files) == 0 or files[0].filename == '':
        logger.warning("上传的文件名为空")
        return jsonify({'error': '没有选择文件'}), 400
    
    # 生成唯一的临时目录
    session_id = str(uuid.uuid4())
    logger.info(f"创建会话: {session_id}")
    
    temp_folder = os.path.join(current_app.config['TEMP_FOLDER'], session_id)
    os.makedirs(temp_folder, exist_ok=True)
    
    extract_dir = os.path.join(temp_folder, 'extracted')
    os.makedirs(extract_dir, exist_ok=True)
    
    all_results = []
    
    try:
        logger.info(f"开始处理 {len(files)} 个上传的ZIP文件")
        
        for file in files:
            # 检查文件类型
            if not allowed_file(file.filename):
                logger.warning(f"不支持的文件类型: {file.filename}")
                continue
                
            # 保存文件
            filename = secure_filename(file.filename)
            zip_path = os.path.join(temp_folder, filename)
            file.save(zip_path)
            logger.info(f"文件已保存到: {zip_path}")
            
            # 为每个ZIP文件创建单独的提取目录
            file_extract_dir = os.path.join(extract_dir, os.path.splitext(filename)[0])
            os.makedirs(file_extract_dir, exist_ok=True)
            
            # 解压文件
            try:
                extract_zip(zip_path, file_extract_dir)
                
                # 处理PDF文件
                results = process_pdf_files(file_extract_dir)
                all_results.extend(results)
                
            except Exception as e:
                logger.error(f"处理文件 {filename} 时出错: {str(e)}", exc_info=True)
                # 如果一个ZIP文件处理失败，继续处理其他文件
                continue
        
        if not all_results:
            logger.warning("没有成功处理任何订单")
            return jsonify({'error': '没有成功处理任何订单'}), 400
            
        # 获取用户MAC地址
        mac_address = get_user_mac()
        logger.info(f"用户MAC地址: {mac_address}")
        
        # 保存用户数据
        total_amount = sum(result.get('amount', 0) for result in all_results)
        save_user_data(mac_address, len(all_results), total_amount, [result.get('order_id') for result in all_results])
        logger.info(f"用户数据已保存，订单数: {len(all_results)}, 总金额: {total_amount}")
        
        # 返回处理结果
        logger.info(f"文件处理完成，成功处理 {len(all_results)} 个订单")
        return jsonify({
            'success': True,
            'message': f'成功处理 {len(all_results)} 个订单',
            'results': all_results
        })
        
    except Exception as e:
        logger.error(f"处理文件时出错: {str(e)}", exc_info=True)
        return jsonify({'error': f'处理文件时出错: {str(e)}'}), 500

@main_bp.route('/api/print/<filename>', methods=['POST'])
def print_file(filename):
    """打印指定的PDF文件"""
    logger = current_app.logger
    logger.info(f"收到打印请求: {filename}")
    
    try:
        file_path = os.path.join(current_app.config['OUTPUT_FOLDER'], filename)
        if not os.path.exists(file_path):
            logger.warning(f"文件不存在: {file_path}")
            return jsonify({'error': '文件不存在'}), 404
        
        print_result = print_pdf(file_path)
        logger.info(f"文件已发送至打印机: {file_path}")
        return jsonify({'success': True, 'message': '文件已发送至打印机'})
    except Exception as e:
        logger.error(f"打印文件时出错: {str(e)}", exc_info=True)
        return jsonify({'error': f'打印文件时出错: {str(e)}'}), 500

@main_bp.route('/api/statistics', methods=['GET'])
def get_statistics():
    """获取所有用户的统计数据"""
    logger = current_app.logger
    logger.info("收到获取统计数据请求")
    
    try:
        stats = get_all_user_stats()
        logger.info(f"返回统计数据，用户数: {len(stats)}")
        return jsonify(stats)
    except Exception as e:
        logger.error(f"获取统计数据时出错: {str(e)}", exc_info=True)
        return jsonify({'error': f'获取统计数据时出错: {str(e)}'}), 500

@main_bp.route('/output/<filename>')
def get_output_file(filename):
    """获取生成的PDF文件"""
    logger = current_app.logger
    logger.debug(f"请求获取输出文件: {filename}")
    return send_from_directory(current_app.config['OUTPUT_FOLDER'], filename) 