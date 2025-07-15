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
    return render_template('index.html')

@main_bp.route('/statistics')
def statistics():
    """渲染统计页面"""
    return render_template('statistics.html')

@main_bp.route('/api/upload', methods=['POST'])
def upload_file():
    """处理文件上传"""
    # 检查是否有文件
    if 'file' not in request.files:
        return jsonify({'error': '没有文件'}), 400
    
    file = request.files['file']
    
    # 检查文件名
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    
    # 检查文件类型
    if not allowed_file(file.filename):
        return jsonify({'error': '不支持的文件类型，请上传ZIP文件'}), 400
    
    # 保存文件
    filename = secure_filename(file.filename)
    temp_folder = os.path.join(current_app.config['TEMP_FOLDER'], str(uuid.uuid4()))
    os.makedirs(temp_folder, exist_ok=True)
    
    zip_path = os.path.join(temp_folder, filename)
    file.save(zip_path)
    
    # 解压文件
    extract_dir = os.path.join(temp_folder, 'extracted')
    os.makedirs(extract_dir, exist_ok=True)
    
    try:
        extract_zip(zip_path, extract_dir)
        
        # 处理PDF文件
        results = process_pdf_files(extract_dir)
        
        # 获取用户MAC地址
        mac_address = get_user_mac()
        
        # 保存用户数据
        total_amount = sum(result.get('amount', 0) for result in results)
        save_user_data(mac_address, len(results), total_amount, [result.get('order_id') for result in results])
        
        # 返回处理结果
        return jsonify({
            'success': True,
            'message': f'成功处理 {len(results)} 个订单',
            'results': results
        })
        
    except Exception as e:
        return jsonify({'error': f'处理文件时出错: {str(e)}'}), 500

@main_bp.route('/api/print/<filename>', methods=['POST'])
def print_file(filename):
    """打印指定的PDF文件"""
    try:
        file_path = os.path.join(current_app.config['OUTPUT_FOLDER'], filename)
        if not os.path.exists(file_path):
            return jsonify({'error': '文件不存在'}), 404
        
        print_result = print_pdf(file_path)
        return jsonify({'success': True, 'message': '文件已发送至打印机'})
    except Exception as e:
        return jsonify({'error': f'打印文件时出错: {str(e)}'}), 500

@main_bp.route('/api/statistics', methods=['GET'])
def get_statistics():
    """获取所有用户的统计数据"""
    try:
        stats = get_all_user_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': f'获取统计数据时出错: {str(e)}'}), 500

@main_bp.route('/output/<filename>')
def get_output_file(filename):
    """获取生成的PDF文件"""
    return send_from_directory(current_app.config['OUTPUT_FOLDER'], filename) 