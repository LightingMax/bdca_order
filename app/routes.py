import os
import uuid
import datetime
from flask import Blueprint, render_template, request, jsonify, current_app, send_from_directory
from werkzeug.utils import secure_filename

from app.services.file_service import (
    allowed_file, extract_zip, calculate_file_hash, 
    check_file_exists, save_file_hash, check_order_processed,
    get_processed_orders
)
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
    
    # 获取已处理过的订单ID列表
    processed_order_ids = set(get_processed_orders())
    logger.info(f"已处理过的订单数量: {len(processed_order_ids)}")
    
    all_results = []       # 所有处理结果（包括重用的）
    new_results = []       # 只包含新处理的结果
    processed_files = []
    reused_files = []
    
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
            
            # 计算文件哈希
            file_hash = calculate_file_hash(zip_path)
            logger.info(f"文件 {filename} 的哈希值: {file_hash}")
            
            # 检查文件是否已上传过
            existing_file = check_file_exists(file_hash)
            if existing_file:
                logger.info(f"文件 {filename} 已上传过，重用之前的处理结果")
                
                # 如果文件已上传过，使用之前的处理结果
                if 'results' in existing_file:
                    # 将已有结果添加到总结果中
                    all_results.extend(existing_file['results'])
                    reused_files.append({
                        'filename': filename,
                        'hash': file_hash,
                        'original_upload_time': existing_file.get('upload_time', '未知'),
                        'result_count': len(existing_file['results'])
                    })
                    continue
                else:
                    logger.warning(f"文件 {filename} 之前的处理结果不完整，将重新处理")
            
            # 为每个ZIP文件创建单独的提取目录
            file_extract_dir = os.path.join(extract_dir, os.path.splitext(filename)[0])
            os.makedirs(file_extract_dir, exist_ok=True)
            
            # 解压文件
            try:
                extract_zip(zip_path, file_extract_dir)
                
                # 处理PDF文件
                results = process_pdf_files(file_extract_dir)
                
                # 过滤结果，找出新的订单
                file_new_results = []
                for result in results:
                    order_id = result.get('order_id')
                    if order_id and order_id not in processed_order_ids:
                        file_new_results.append(result)
                        processed_order_ids.add(order_id)  # 添加到已处理列表中
                        new_results.append(result)  # 记录新处理的结果
                
                # 添加所有结果到总结果列表
                all_results.extend(results)
                
                # 保存文件哈希和处理结果
                file_info = {
                    'filename': filename,
                    'upload_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'session_id': session_id,
                    'results': results
                }
                save_file_hash(file_hash, file_info)
                
                processed_files.append({
                    'filename': filename,
                    'hash': file_hash,
                    'result_count': len(results),
                    'new_result_count': len(file_new_results)
                })
                
                logger.info(f"文件 {filename} 处理完成，订单总数: {len(results)}，新订单数: {len(file_new_results)}")
                
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
        
        # 保存用户数据（只记录新处理的订单）
        if new_results:
            total_new_amount = sum(result.get('amount', 0) for result in new_results)
            save_user_data(mac_address, len(new_results), total_new_amount, [result.get('order_id') for result in new_results])
            logger.info(f"用户数据已保存，新订单数: {len(new_results)}, 新增金额: {total_new_amount}")
        else:
            logger.info("没有新处理的订单，不更新用户统计数据")
        
        # 计算总金额（所有订单）
        total_amount = sum(result.get('amount', 0) for result in all_results)
        
        # 返回处理结果
        logger.info(f"文件处理完成，成功处理 {len(all_results)} 个订单，其中新处理 {len(new_results)} 个")
        return jsonify({
            'success': True,
            'message': f'成功处理 {len(all_results)} 个订单',
            'results': all_results,
            'processed_files': len(processed_files),
            'reused_files': len(reused_files),
            'new_results_count': len(new_results),
            'total_amount': total_amount,
            'file_details': {
                'processed': processed_files,
                'reused': reused_files
            }
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