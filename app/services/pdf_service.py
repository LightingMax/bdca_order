import os
import re
import uuid
import xml.etree.ElementTree as ET
from PyPDF2 import PdfReader, PdfWriter
from flask import current_app
from app.services.file_service import get_file_paths, group_files_by_type

def extract_amount_from_xml(xml_path):
    """从XML文件中提取订单金额"""
    logger = current_app.logger
    try:
        logger.info(f"正在从XML文件提取金额: {xml_path}")
        
        # 首先尝试从文件名提取金额
        filename = os.path.basename(xml_path)
        amount_match = re.search(r'(\d+\.\d+)元', filename)
        if not amount_match:
            amount_match = re.search(r'-(\d+\.\d+)元?-', filename)
        if not amount_match:
            amount_match = re.search(r'-(\d+\.\d+)-', filename)
            
        if amount_match:
            amount = float(amount_match.group(1))
            logger.info(f"从文件名中提取到金额: {amount}")
            return amount
            
        # 如果文件名中没有金额，解析XML文件
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # 尝试查找常见的金额标签
        # 1. 尝试查找TotalTax-includedAmount标签（示例XML中的格式）
        amount_elem = root.find(".//TotalTax-includedAmount")
        if amount_elem is not None and amount_elem.text:
            try:
                amount = float(amount_elem.text)
                logger.info(f"从TotalTax-includedAmount标签中提取到金额: {amount}")
                return amount
            except ValueError:
                logger.warning(f"无法将TotalTax-includedAmount标签值转换为浮点数: {amount_elem.text}")
        
        # 2. 尝试其他可能的标签
        possible_tags = [
            ".//Amount", 
            ".//TotalAmount", 
            ".//Price", 
            ".//TotaltaxIncludedAmount",
            ".//BasicInformation/TotalAmWithoutTax"
        ]
        
        for tag in possible_tags:
            amount_elem = root.find(tag)
            if amount_elem is not None and amount_elem.text:
                try:
                    amount = float(amount_elem.text)
                    logger.info(f"从{tag}标签中提取到金额: {amount}")
                    return amount
                except ValueError:
                    continue
        
        # 3. 如果没有找到特定标签，尝试在整个XML文本中搜索金额模式
        xml_text = ET.tostring(root, encoding='utf-8').decode('utf-8')
        
        # 尝试匹配常见的金额模式
        amount_patterns = [
            r'TotalTax-includedAmount>(\d+\.\d+)<',
            r'TotaltaxIncludedAmount>(\d+\.\d+)<',
            r'Amount>(\d+\.\d+)<',
            r'金额[：:]\s*(\d+\.\d+)',
            r'总金额[：:]\s*(\d+\.\d+)'
        ]
        
        for pattern in amount_patterns:
            amount_matches = re.findall(pattern, xml_text)
            if amount_matches:
                amount = float(amount_matches[0])
                logger.info(f"从XML文本中使用模式'{pattern}'提取到金额: {amount}")
                return amount
        
        # 如果以上都失败，返回0
        logger.warning(f"无法从XML文件中提取金额: {xml_path}")
        return 0
    except Exception as e:
        logger.error(f"解析XML文件出错: {str(e)}")
        return 0

def identify_pdf_type(pdf_path):
    """识别PDF文件类型（行程单或发票）"""
    logger = current_app.logger
    try:
        filename = os.path.basename(pdf_path).lower()
        logger.info(f"正在识别PDF类型: {pdf_path}")
        
        # 通过文件名判断
        if '发票' in filename or 'invoice' in filename or 'receipt' in filename:
            logger.info(f"通过文件名识别为发票: {pdf_path}")
            return 'invoice'
        elif '行程' in filename or 'itinerary' in filename or 'trip' in filename:
            logger.info(f"通过文件名识别为行程单: {pdf_path}")
            return 'itinerary'
        
        # 通过文件内容判断（简单版）
        reader = PdfReader(pdf_path)
        if len(reader.pages) > 0:
            text = reader.pages[0].extract_text().lower()
            if '发票' in text or 'invoice' in text or 'receipt' in text:
                logger.info(f"通过内容识别为发票: {pdf_path}")
                return 'invoice'
            elif '行程' in text or 'itinerary' in text or 'trip' in text:
                logger.info(f"通过内容识别为行程单: {pdf_path}")
                return 'itinerary'
        
        # 默认返回未知类型
        logger.warning(f"无法识别PDF类型: {pdf_path}")
        return 'unknown'
    except Exception as e:
        logger.error(f"识别PDF类型出错: {str(e)}")
        return 'unknown'

def extract_order_id(file_path):
    """从文件名或内容中提取订单ID - 支持服务商前缀和发票【】格式"""
    logger = current_app.logger
    try:
        logger.info(f"正在提取订单ID: {file_path}")
        filename = os.path.basename(file_path)
        
        # 方法0: 最高优先级 - 从发票文件名中提取【】内的内容
        # 支持格式：【及时用车-53.21元-2个行程】高德打车电子发票
        bracket_pattern = r'【([^】]+)】'
        bracket_match = re.search(bracket_pattern, filename)
        if bracket_match:
            bracket_content = bracket_match.group(1)
            logger.info(f"从发票文件名【】中提取到内容: {bracket_content}")
            return bracket_content
        
        logger.info(f"文件名 '{filename}' 未匹配【】格式，继续尝试其他方法")
        
        # 方法1: 尝试从文件名中提取完整的订单信息
        # 支持格式：阳光出行-32.13元-3个行程、T3-77.06-1等
        order_patterns = [
            r'([^-]+)-(\d+\.\d+)元?-(\d+)个行程',  # 阳光出行-32.13元-3个行程
            r'([^-]+)-(\d+\.\d+)-(\d+)',           # T3-77.06-1
            r'([^-]+)-(\d+\.\d+)',                 # 服务商-金额
            r'订单(\d+)',                           # 订单12345
            r'trip(\d+)',                           # trip001
        ]
        
        # 但是，如果文件名包含"订单-"这种格式，我们优先尝试生成更好的格式
        if '订单-' in filename:
            logger.info(f"检测到'订单-'格式，尝试生成更好的订单ID")
            # 尝试从文件名中提取金额和数量
            amount_match = re.search(r'订单-(\d+\.\d+)-(\d+)', filename)
            if amount_match:
                amount, count = amount_match.groups()
                # 生成更友好的格式：T3出行-77.06元-1个行程
                # 这里可以根据金额和数量生成一个更有意义的ID
                smart_id = f"T3出行-{amount}元-{count}个行程"
                logger.info(f"生成智能订单ID: {smart_id}")
                return smart_id
        
        for pattern in order_patterns:
            match = re.search(pattern, filename)
            if match:
                if len(match.groups()) == 3:
                    # 格式：服务商-金额-数量
                    service, amount, count = match.groups()
                    # 验证服务商名称不为空
                    if service and service.strip():
                        order_id = f"{service}-{amount}-{count}"
                        logger.info(f"从文件名中提取到订单ID: {order_id}")
                        return order_id
                    else:
                        logger.warning(f"服务商名称为空，跳过模式: {pattern}")
                        continue
                elif len(match.groups()) == 2:
                    # 格式：服务商-金额
                    service, amount = match.groups()
                    # 验证服务商名称不为空
                    if service and service.strip():
                        order_id = f"{service}-{amount}"
                        logger.info(f"从文件名中提取到订单ID: {order_id}")
                        return order_id
                    else:
                        logger.warning(f"服务商名称为空，跳过模式: {pattern}")
                        continue
                elif len(match.groups()) == 1:
                    # 格式：订单号或trip号
                    order_id = match.group(1)
                    logger.info(f"从文件名中提取到订单ID: {order_id}")
                    return order_id
        
        # 方法2: 尝试查找6位以上的数字作为订单ID
        order_id_match = re.search(r'(\d{6,})', filename)
        if order_id_match:
            order_id = order_id_match.group(1)
            logger.info(f"从文件名中提取到数字订单ID: {order_id}")
            return order_id
        
        # 方法3: 如果是PDF，尝试从内容中提取
        if file_path.lower().endswith('.pdf'):
            try:
                reader = PdfReader(file_path)
                if len(reader.pages) > 0:
                    text = reader.pages[0].extract_text()
                    # 尝试查找订单号模式
                    order_id_match = re.search(r'订单[号#]?[：:]?\s*(\d{6,})', text)
                    if order_id_match:
                        order_id = order_id_match.group(1)
                        logger.info(f"从PDF内容中提取到订单ID: {order_id}")
                        return order_id
            except Exception as e:
                logger.warning(f"从PDF内容提取订单ID失败: {e}")
        
        # 方法4: 如果是XML，尝试从内容中提取
        if file_path.lower().endswith('.xml'):
            try:
                tree = ET.parse(file_path)
                root = tree.getroot()
                # 尝试查找订单号元素
                order_elem = root.find(".//OrderID") or root.find(".//OrderNumber")
                if order_elem is not None and order_elem.text:
                    order_id = order_elem.text
                    logger.info(f"从XML内容中提取到订单ID: {order_id}")
                    return order_id
            except Exception as e:
                logger.warning(f"从XML内容提取订单ID失败: {e}")
        
        # 方法5: 生成基于服务商的智能订单ID
        smart_order_id = generate_smart_order_id(filename)
        if smart_order_id:
            logger.info(f"生成智能订单ID: {smart_order_id}")
            return smart_order_id
        
        # 方法6: 如果所有方法都失败，使用文件名的ASCII部分作为标识
        ascii_filename = ''.join(c for c in os.path.splitext(filename)[0] if ord(c) < 128)
        if not ascii_filename:
            ascii_filename = str(uuid.uuid4())[:8]
        
        logger.warning(f"无法提取订单ID，使用文件名作为标识: {ascii_filename}")
        return ascii_filename
        
    except Exception as e:
        logger.error(f"提取订单ID出错: {str(e)}")
        random_id = str(uuid.uuid4())[:8]
        logger.info(f"使用随机ID作为后备: {random_id}")
        return random_id  # 生成随机ID作为后备


def generate_smart_order_id(filename):
    """
    生成智能订单ID - 修正版
    1. 优先提取【】中的内容。
    2. 修复'订单-'开头的格式。
    3. 对于已符合标准格式但无特殊符号的文件，去除扩展名后返回。
    """
    try:
        # 移除文件扩展名，方便处理
        name_only = os.path.splitext(filename)[0]

        # 核心逻辑：定义模式并按优先级排序
        patterns = [
            # 优先级 1: 最高优先级 - 提取【】内的完整内容
            (r'【([^】]+)】', lambda m: m.group(1)),
            
            # 优先级 2: 修复 '订单-' 开头的格式
            (r'^订单-(\d+\.\d+)-(\d+)$', lambda m: f"T3出行-{m.group(1)}元-{m.group(2)}个行程"),
            
            # 优先级 2.5: 修复 '订单T3-' 开头的格式
            (r'^订单T3-(\d+\.\d+)-(\d+)$', lambda m: f"T3出行-{m.group(1)}元-{m.group(2)}个行程"),
            
            # 优先级 3: 匹配标准格式（为了防止它被下面的逻辑捕获）
            (r'^[^-]+-\d+\.\d+元?-\d+个行程$', lambda m: m.group(0)),

            # 优先级 4: 匹配简化的 '服务商-金额-数量' 格式
            (r'^([^-]+)-(\d+\.\d+)-(\d+)$', lambda m: f"{m.group(1)}-{m.group(2)}元-{m.group(3)}个行程"),
        ]
        
        for pattern, formatter in patterns:
            # 我们在去除扩展名的文件名上进行匹配
            match = re.search(pattern, name_only)
            if match:
                result = formatter(match)
                logger.info(f"文件名 '{filename}' 匹配模式 '{pattern}'，生成结果: '{result}'")
                return result
        
        logger.info(f"文件名 '{filename}' 未匹配任何模式，返回原文件名: '{name_only}'")
        
        # 如果以上所有特殊规则都未匹配，说明它可能是“其他格式”
        # 直接返回去除扩展名后的文件名
        return name_only
        
    except Exception as e:
        logger.warning(f"生成智能订单ID失败: {filename}, 错误: {e}")
        return None

def match_files_by_order(pdf_files, xml_files):
    """将PDF和XML文件按订单匹配"""
    logger = current_app.logger
    logger.info(f"开始匹配文件，PDF文件数: {len(pdf_files)}，XML文件数: {len(xml_files)}")
    
    orders = {}
    
    # 处理XML文件
    for xml_path in xml_files:
        logger.info(f"正在处理XML文件: {xml_path}")
        order_id = extract_order_id(xml_path)
        logger.info(f"从XML文件提取到订单ID: '{order_id}'")
        amount = extract_amount_from_xml(xml_path)
        
        if order_id not in orders:
            orders[order_id] = {'xml': xml_path, 'amount': amount, 'pdfs': {'invoice': None, 'itinerary': None}}
            logger.info(f"创建新订单: {order_id}, 金额: {amount}")
        else:
            orders[order_id]['xml'] = xml_path
            orders[order_id]['amount'] = amount
            logger.info(f"更新订单信息: {order_id}, 金额: {amount}")
    
    # 处理PDF文件
    for pdf_path in pdf_files:
        logger.info(f"正在处理PDF文件: {pdf_path}")
        order_id = extract_order_id(pdf_path)
        logger.info(f"从PDF文件提取到订单ID: '{order_id}'")
        pdf_type = identify_pdf_type(pdf_path)
        logger.info(f"PDF文件类型: {pdf_type}")
        
        if pdf_type != 'unknown':
            if order_id not in orders:
                orders[order_id] = {'xml': None, 'amount': 0, 'pdfs': {'invoice': None, 'itinerary': None}}
                logger.info(f"创建新订单(来自PDF): {order_id}")
            
            orders[order_id]['pdfs'][pdf_type] = pdf_path
            logger.info(f"为订单 {order_id} 添加 {pdf_type} 类型的PDF: {pdf_path}")
    
    logger.info(f"文件匹配完成，共找到 {len(orders)} 个订单")
    return orders

def merge_pdfs(itinerary_path, invoice_path, output_path):
    """合并行程单和发票PDF，并调整为一页显示"""
    logger = current_app.logger
    logger.info(f"开始合并PDF，行程单: {itinerary_path}, 发票: {invoice_path}")
    
    # 从文件名中 匹配发票/行程单中包含的行程数量 （实例文件名 【阳光出行-32.13元-3个行程】高德打车电子发票，匹配其中的3个行程）
    itinerary_name = os.path.basename(itinerary_path)
    invoice_name = os.path.basename(invoice_path)
    itinerary_match = re.search(r'-(\d+)个行程', itinerary_name)
    invoice_match = re.search(r'-(\d+)个行程', invoice_name)
    itinerary_count = int(itinerary_match.group(1)) if itinerary_match else 1
    invoice_count = int(invoice_match.group(1)) if invoice_match else 1
    
    assert itinerary_count == invoice_count, "行程单和发票的行程数量不一致"
    
    # 方法1：优先使用pdftk进行快速合并（毫秒级，推荐）
    try:
        import subprocess
        logger.info("🚀 使用pdftk进行超快速PDF合并...")
        
        # 使用pdftk cat进行垂直拼接
        subprocess.run([
            'pdftk', invoice_path, itinerary_path, 
            'cat', 'output', output_path
        ], check=True, timeout=5)  # 设置5秒超时
        
        logger.info("✅ 使用pdftk超快速合并成功")
        return output_path
        
    except (ImportError, subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        logger.info(f"pdftk不可用或失败，尝试PyPDF2: {e}")
        
        # 方法2：使用PyPDF2进行快速合并（秒级）
        try:
            from PyPDF2 import PdfReader, PdfWriter
            logger.info("🔄 使用PyPDF2进行快速PDF合并...")
            
            # 读取两个PDF文件
            with open(invoice_path, 'rb') as invoice_file:
                invoice_reader = PdfReader(invoice_file)
                invoice_page = invoice_reader.pages[0]
            
            with open(itinerary_path, 'rb') as itinerary_file:
                itinerary_reader = PdfReader(itinerary_file)
                itinerary_page = itinerary_reader.pages[0]
            
            # 创建新的PDF
            writer = PdfWriter()
            writer.add_page(invoice_page)
            writer.add_page(itinerary_page)
            
            # 保存合并后的PDF
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
            logger.info("✅ 使用PyPDF2快速合并成功")
            return output_path
            
        except ImportError:
            logger.info("PyPDF2不可用，回退到图像处理方式")
        except Exception as e:
            logger.info(f"PyPDF2合并失败: {e}")
        
        # 方法3：回退到原有的图像处理方式（慢速，最后备选）
        logger.info("⚠️ 回退到图像处理方式（较慢）")
        A4_WIDTH, A4_HEIGHT = 2480, 3508
        # 定义页边距（像素）
        MARGIN = 100
        # 考虑页边距后的实际可用宽度和高度
        USABLE_WIDTH = A4_WIDTH - 2 * MARGIN
        USABLE_HEIGHT = A4_HEIGHT - 2 * MARGIN
        
        per_count_height = USABLE_HEIGHT / 21
        try:
            from pdf2image import convert_from_path
            from PIL import Image
            images = convert_from_path(itinerary_path,dpi=300)
            itinerary_image = images[0]
            w, h = itinerary_image.size
            # 计算需要裁剪的区域 去除部分顶部无关内容
            top_half = itinerary_image.crop((0, 4*per_count_height, w, h // 2+ per_count_height*(itinerary_count-1)))
            
            # resize top_half
            ratio = USABLE_WIDTH / top_half.width
            new_size = (USABLE_WIDTH, int(USABLE_HEIGHT*0.6))
            top_half = top_half.resize(new_size)
            
            images = convert_from_path(invoice_path,dpi=300)
            invoice_image = images[0]
            
            ratio = 0.9*USABLE_WIDTH / invoice_image.width
            new_size = (USABLE_WIDTH, int(USABLE_HEIGHT * 0.4))
            invoice_image = invoice_image.resize(new_size)
            
            combined = Image.new("RGB", (A4_WIDTH, A4_HEIGHT), (255, 255, 255))

            # 粘贴上半部分（考虑页边距）
            combined.paste(top_half, (MARGIN, MARGIN))

            # 粘贴下半部分（考虑页边距）
            combined.paste(invoice_image, (MARGIN, MARGIN + top_half.height))
            
            # 最后再缩放到A4纸
            combined = combined.resize((A4_WIDTH, A4_HEIGHT))
            
            combined.save(output_path)
            
        except Exception as e:
            logger.error(f"合并PDF时出错: {str(e)}")
            raise
        
        return output_path

def process_pdf_files(extract_dir):
    """处理解压后的PDF和XML文件"""
    logger = current_app.logger
    logger.info(f"开始处理解压后的文件: {extract_dir}")
    
    # 获取所有文件路径
    file_paths = get_file_paths(extract_dir)
    grouped_files = group_files_by_type(file_paths)
    
    # 按订单匹配文件
    orders = match_files_by_order(grouped_files['pdf'], grouped_files['xml'])
    
    results = []
    
    # 处理每个订单
    order_count = 0
    for order_id, order_data in orders.items():
        # 检查是否有足够的文件进行处理
        itinerary_path = order_data['pdfs']['itinerary']
        invoice_path = order_data['pdfs']['invoice']
        
        if not itinerary_path and not invoice_path:
            logger.warning(f"订单 {order_id} 没有PDF文件，跳过处理")
            continue
        
        # 使用简单的序号作为文件名前缀，避免使用中文文件名
        order_count += 1
        
        # 生成输出文件名 (使用序号和随机字符串，避免使用可能包含中文的order_id)
        output_filename = f"order_{order_count}_{uuid.uuid4().hex[:8]}.pdf"
        output_path = os.path.join(current_app.config['OUTPUT_FOLDER'], output_filename)
        
        logger.info(f"处理订单 {order_id} (序号 {order_count})，输出文件: {output_filename}")
        
        # 合并PDF
        try:
            merge_pdfs(itinerary_path, invoice_path, output_path)
            
            # 添加处理结果
            results.append({
                'order_id': order_id,
                'amount': order_data['amount'],
                'output_file': output_filename,
                'has_itinerary': itinerary_path is not None,
                'has_invoice': invoice_path is not None
            })
            logger.info(f"订单 {order_id} 处理成功")
        except Exception as e:
            logger.error(f"处理订单 {order_id} 时出错: {str(e)}")
    
    logger.info(f"所有订单处理完成，成功处理 {len(results)} 个订单")
    return results 