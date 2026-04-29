import re
import uuid
import xml.etree.ElementTree as ET
import os
import requests
import json
from pathlib import Path
from PyPDF2 import PdfReader, PdfWriter
from flask import current_app
from app.services.file_service import get_file_paths, group_files_by_type

# ============================================================================
# 以下函数已废弃，改用高德打车PDF解析器（parse_gaode_itinerary_enhanced）
# ============================================================================
# def call_qwen_api_for_trips(table_data_list):
#     """调用通义千问API规整行程数据（已废弃，改用高德打车PDF解析器）"""
#     logger = current_app.logger
#     
#     # 从配置文件获取通义千问API配置
#     url = f"{current_app.config['QWEN_API_BASE_URL']}/chat/completions"
#     headers = {
#         "Authorization": f"Bearer {current_app.config['QWEN_API_KEY']}",
#         "Content-Type": "application/json"
#     }
#     
#     # 构建提示词
#     prompt = f"""
# 请帮我整理以下行程记录：将它们按照上车时间升序排列并重新编号，然后以JSON格式返回结果。每个行程记录应包含序号、服务商、车型、上车时间、城市、起点、终点和金额等所有字段。请确保返回标准的JSON数组格式，无需添加任何额外解释。
# 
# 原始表格数据：
# {table_data_list}
# 
# 请返回JSON数组格式，每个对象包含以下字段：
# - sequence: 序号（字符串）
# - service_provider: 服务商（字符串）
# - car_type: 车型（字符串）
# - pickup_time: 上车时间（字符串）
# - city: 城市（字符串）
# - start_point: 起点（字符串）
# - end_point: 终点（字符串）
# - amount: 金额（字符串）
# """
#     
#     data = {
#         "model": current_app.config['QWEN_MODEL'],
#         "messages": [
#             {"role": "user", "content": prompt}
#         ],
#         "temperature": 0.1
#     }
#     
#     try:
#         import time
#         start_time = time.time()
#         
#         logger.info("调用通义千问API规整行程数据...")
#         logger.info(f"API请求URL: {url}")
#         logger.info(f"API超时设置: {current_app.config['QWEN_API_TIMEOUT']} 秒")
#         logger.info(f"请求数据大小: {len(str(table_data_list))} 字符")
#         logger.info(f"请求开始时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}")
#         
#         response = requests.post(url, headers=headers, json=data, timeout=current_app.config['QWEN_API_TIMEOUT'])
#         
#         end_time = time.time()
#         duration = end_time - start_time
#         logger.info(f"API请求完成，耗时: {duration:.2f} 秒")
#         response.raise_for_status()
#         result = response.json()
#         content = result['choices'][0]['message']['content']
#         
#         logger.info(f"通义千问API原始返回内容长度: {len(content)} 字符")
#         logger.info(f"通义千问API原始返回内容: {content[:500]}...")  # 只显示前500字符
#         
#         # 提取JSON部分
#         import re
#         json_match = re.search(r'\[.*\]', content, re.DOTALL)
#         if json_match:
#             json_str = json_match.group()
#             logger.info(f"提取到的JSON字符串长度: {len(json_str)} 字符")
#             logger.info(f"提取到的JSON字符串: {json_str}")
#             
#             parsed_data = json.loads(json_str)
#             logger.info(f"通义千问API成功规整了 {len(parsed_data)} 个行程")
#             
#             # 详细输出每个行程的信息
#             for i, trip in enumerate(parsed_data):
#                 logger.info(f"行程{i+1}: 序号={trip.get('sequence')}, 服务商={trip.get('service_provider')}, 时间={trip.get('pickup_time')}, 起点={trip.get('start_point')}, 终点={trip.get('end_point')}, 金额={trip.get('amount')}")
#             
#             return parsed_data
#         else:
#             logger.error("通义千问API返回结果中未找到JSON数据")
#             logger.error(f"完整返回内容: {content}")
#             return []
#             
#     except Exception as e:
#         logger.error(f"调用通义千问API失败: {e}")
#         logger.error(f"请求数据: {data}")
#         return []

def extract_amount_from_xml(xml_path):
    """从XML文件中提取订单金额"""
    logger = current_app.logger
    try:
        logger.info(f"正在从XML文件提取金额: {xml_path}")
        
        # 首先尝试从文件名提取金额
        filename = Path(xml_path).name
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


def extract_amount_from_pdf(pdf_path):
    """从PDF文件中提取金额（轻量级方法）"""
    logger = current_app.logger

    def _extract_amount_from_text(full_text):
        # 部分电子发票使用 UniGB 编码，PyPDF2 兜底提取时数字间可能夹杂 \x00。
        full_text = (full_text or "").replace("\x00", "")
        amount_patterns = [
            r'[¥￥]\s*(\d+\.\d{1,2})',
            r'价税合计[（(]小写[）)]\s*[¥￥]?\s*(\d+\.\d{1,2})',
            r'价税合计[：:\s]*[¥￥]?\s*(\d+\.\d{1,2})',
            r'合计金额[：:\s]*[¥￥]?\s*(\d+\.\d{1,2})',
            r'总金额[：:\s]*[¥￥]?\s*(\d+\.\d{1,2})',
            r'金额[：:\s]*[¥￥]?\s*(\d+\.\d{1,2})',
            r'(\d+\.\d{2})元?',
            r'(\d+\.\d{1,2})',
        ]
        for pattern in amount_patterns:
            matches = re.findall(pattern, full_text)
            valid_amounts = []
            for match in matches:
                try:
                    amount = float(match)
                except (TypeError, ValueError):
                    continue
                if 1.0 <= amount <= 10000.0:
                    valid_amounts.append(amount)
            if valid_amounts:
                amount = max(valid_amounts)
                logger.info(f"从PDF文本中使用模式'{pattern}'提取到金额: {amount}")
                return amount
        return 0

    try:
        logger.info(f"正在从PDF文件提取金额: {pdf_path}")
        
        # 首先尝试从文件名提取金额
        filename = Path(pdf_path).name
        amount_match = re.search(r'(\d+\.\d+)元', filename)
        if not amount_match:
            amount_match = re.search(r'-(\d+\.\d+)元?-', filename)
        if not amount_match:
            amount_match = re.search(r'-(\d+\.\d+)-', filename)
            
        if amount_match:
            amount = float(amount_match.group(1))
            logger.info(f"从PDF文件名中提取到金额: {amount}")
            return amount
        
        # 使用PyMuPDF (fitz)提取PDF文本内容
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(pdf_path)
            if len(doc) == 0:
                logger.warning(f"PDF文件没有页面: {pdf_path}")
                doc.close()
                return 0
            
            # 提取所有页面的文本
            full_text = ""
            for page_num in range(len(doc)):
                try:
                    page = doc.load_page(page_num)
                    page_text = page.get_text()
                    if page_text:
                        full_text += page_text + "\n"
                except Exception as e:
                    logger.warning(f"提取第{page_num+1}页文本失败: {e}")
                    continue
            
            doc.close()
            
            if not full_text.strip():
                logger.warning(f"PDF文件没有可提取的文本内容: {pdf_path}")
                return 0
            
            logger.info(f"成功提取PDF文本，长度: {len(full_text)} 字符")
            
            amount = _extract_amount_from_text(full_text)
            if amount > 0:
                return amount
            
            # 如果正则匹配失败，尝试查找包含"元"的数字
            yuan_matches = re.findall(r'(\d+\.\d{2})元', full_text)
            if yuan_matches:
                amounts = [float(match) for match in yuan_matches if 1.0 <= float(match) <= 10000.0]
                if amounts:
                    amount = max(amounts)
                    logger.info(f"从PDF文本中提取到含'元'的金额: {amount}")
                    return amount
            
            logger.warning(f"无法从PDF文件中提取金额: {pdf_path}")
            return 0
            
        except Exception as e:
            logger.warning(f"使用PyMuPDF(fitz)提取PDF文本失败，尝试PyPDF2兜底: {e}")
            try:
                reader = PdfReader(pdf_path)
                full_text = "\n".join((page.extract_text() or "") for page in reader.pages)
                amount = _extract_amount_from_text(full_text)
                if amount > 0:
                    logger.info(f"使用PyPDF2兜底提取到金额: {amount}")
                    return amount
            except Exception as fallback_e:
                logger.error(f"使用PyPDF2兜底提取PDF文本失败: {fallback_e}")
            return 0
            
    except Exception as e:
        logger.error(f"从PDF文件提取金额出错: {str(e)}")
        return 0

def identify_pdf_type(pdf_path):
    """识别 PDF 文件类型（网约车/酒店/火车票/机票）。"""
    logger = current_app.logger
    try:
        filename = Path(pdf_path).name.lower()
        logger.info(f"正在识别PDF类型: {pdf_path}")

        train_keywords = [
            '火车', '高铁', '铁路', '动车', '乘车', '车票', '报销凭证', '客票',
            'china railway', 'railway', 'ticket', '12306'
        ]
        flight_keywords = [
            '机票', '航班', '飞机票', '航空', '飞猪', '代订机票', 'flight', 'air ticket'
        ]

        # 通过文件名判断
        if any(keyword in filename for keyword in flight_keywords):
            logger.info(f"通过文件名识别为机票: {pdf_path}")
            return 'flight_ticket'
        if any(keyword in filename for keyword in train_keywords):
            logger.info(f"通过文件名识别为火车票: {pdf_path}")
            return 'train_ticket'
        if '发票' in filename or 'invoice' in filename or 'receipt' in filename:
            logger.info(f"通过文件名识别为发票: {pdf_path}")
            return 'invoice'
        elif '行程' in filename or 'itinerary' in filename or 'trip' in filename:
            logger.info(f"通过文件名识别为行程单: {pdf_path}")
            return 'itinerary'
        elif '结账单' in filename or '账单' in filename or 'bill' in filename:
            logger.info(f"通过文件名识别为结账单: {pdf_path}")
            return 'hotel_bill'
        
        # 通过文件内容判断（简单版）
        reader = PdfReader(pdf_path)
        if len(reader.pages) > 0:
            text = (reader.pages[0].extract_text() or '').lower()
            train_no_match = re.search(r'\b[gdcztk]\d{1,4}\b', text, flags=re.IGNORECASE)
            flight_no_match = re.search(r'\b[a-z]{2}\d{3,4}\b', text, flags=re.IGNORECASE)
            if any(keyword in text for keyword in flight_keywords) or flight_no_match:
                logger.info(f"通过内容识别为机票: {pdf_path}")
                return 'flight_ticket'
            if any(keyword in text for keyword in train_keywords) or train_no_match:
                logger.info(f"通过内容识别为火车票: {pdf_path}")
                return 'train_ticket'
            if '发票' in text or 'invoice' in text or 'receipt' in text:
                logger.info(f"通过内容识别为发票: {pdf_path}")
                return 'invoice'
            elif '行程' in text or 'itinerary' in text or 'trip' in text:
                logger.info(f"通过内容识别为行程单: {pdf_path}")
                return 'itinerary'
            elif '结账单' in text or '账单' in text or '客人姓名' in text or '房间号' in text or '入住日期' in text:
                logger.info(f"通过内容识别为结账单: {pdf_path}")
                return 'hotel_bill'
        
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
        filename = Path(file_path).name
        
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
        
        # 方法1.5: 腾讯出行特殊格式处理
        # 支持格式：99.45元-2025年08月12日14时16分腾讯出行电子发票-.pdf
        # 支持格式：99.45元-2025年08月12日14时16分腾讯出行行程单-.pdf
        tencent_pattern = r'(\d+\.\d+)元-(\d{4}年\d{2}月\d{2}日\d{2}时\d{2}分)腾讯出行'
        tencent_match = re.search(tencent_pattern, filename)
        if tencent_match:
            amount, datetime_str = tencent_match.groups()
            # 生成统一的订单ID，不区分发票和行程单
            order_id = f"腾讯出行-{amount}元-{datetime_str}"
            logger.info(f"从腾讯出行文件名提取到订单ID: {order_id}")
            return order_id
        
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
        
        # 方法2.5: 特殊处理华住酒店文件
        # 华住酒店发票格式：dzfp_25114000000003462819_杭州大数云智科技有限公司_20250831201746.pdf
        # 华住酒店结账单格式：结账单20250831.pdf
        if 'dzfp_' in filename and '_' in filename:
            # 提取发票号码作为订单ID
            parts = filename.split('_')
            if len(parts) >= 2:
                invoice_number = parts[1]  # 25114000000003462819
                logger.info(f"从华住酒店发票文件名提取到发票号码: {invoice_number}")
                return invoice_number
        elif '结账单' in filename:
            # 对于结账单，尝试从发票号码中提取日期部分进行匹配
            # 这里我们需要一个更智能的匹配策略
            date_match = re.search(r'(\d{8})', filename)  # 20250831
            if date_match:
                date_str = date_match.group(1)
                logger.info(f"从结账单文件名提取到日期: {date_str}")
                # 返回一个通用的订单ID，让系统能够匹配
                return f"hotel_{date_str}"
        
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
        ascii_filename = ''.join(c for c in Path(filename).stem if ord(c) < 128)
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
    logger = current_app.logger
    try:
        # 移除文件扩展名，方便处理
        name_only = Path(filename).stem

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

    def _is_gaode_taxi_order(order_id, order_data):
        haystack = [str(order_id or '')]
        for pdf_path in (order_data.get('pdfs') or {}).values():
            if pdf_path:
                haystack.append(Path(pdf_path).name)
        text = ' '.join(haystack).lower()
        return any(keyword in text for keyword in ['高德', 'gaode', 'amap'])
    
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
                orders[order_id] = {'xml': None, 'amount': 0, 'pdfs': {'invoice': None, 'itinerary': None, 'hotel_bill': None}}
                logger.info(f"创建新订单(来自PDF): {order_id}")
            
            # 确保pdfs字典包含所有类型
            if 'hotel_bill' not in orders[order_id]['pdfs']:
                orders[order_id]['pdfs']['hotel_bill'] = None
            
            orders[order_id]['pdfs'][pdf_type] = pdf_path
            logger.info(f"为订单 {order_id} 添加 {pdf_type} 类型的PDF: {pdf_path}")
    
    # 检查所有订单的XML状态（针对网约车文件）
    xml_missing_warnings = []
    for order_id, order_data in orders.items():
        if order_data['xml'] is None:
            # XML文件缺失时，尝试从PDF文件名中提取金额
            logger.info(f"🔍 网约车订单 {order_id} 缺少XML文件，尝试从PDF文件名提取金额")
            
            # 尝试从发票PDF文件名提取金额
            if order_data['pdfs'].get('invoice'):
                invoice_amount = extract_amount_from_pdf(order_data['pdfs']['invoice'])
                if invoice_amount > 0:
                    order_data['amount'] = invoice_amount
                    logger.info(f"✅ 从发票文件名成功提取金额: {invoice_amount}元")
                else:
                    # 如果发票文件名提取失败，尝试从行程单文件名提取
                    if order_data['pdfs'].get('itinerary'):
                        itinerary_amount = extract_amount_from_pdf(order_data['pdfs']['itinerary'])
                        if itinerary_amount > 0:
                            order_data['amount'] = itinerary_amount
                            logger.info(f"✅ 从行程单文件名成功提取金额: {itinerary_amount}元")
            
            # 如果仍然没有提取到金额，记录警告
            if order_data['amount'] == 0 and _is_gaode_taxi_order(order_id, order_data):
                xml_missing_warnings.append({
                    'order_id': order_id,
                    'reason': 'XML文件缺失且无法从PDF文件名提取金额',
                    'impact': '金额统计为0，可能不准确',
                    'type': 'taxi'
                })
                logger.warning(f"⚠️ 网约车订单 {order_id} 缺少XML文件且无法从PDF文件名提取金额")
            else:
                logger.info(f"✅ 网约车订单 {order_id} 从PDF文件名成功提取金额: {order_data['amount']}元")
        elif order_data['amount'] == 0 and _is_gaode_taxi_order(order_id, order_data):
            xml_missing_warnings.append({
                'order_id': order_id,
                'reason': 'XML中未找到金额信息',
                'impact': '金额统计为0，可能不准确',
                'type': 'taxi'
            })
            logger.warning(f"⚠️ 网约车订单 {order_id} XML中未找到金额信息，金额统计为0，可能不准确")
    
    logger.info(f"网约车文件匹配完成，共找到 {len(orders)} 个订单，XML缺失警告: {len(xml_missing_warnings)} 个")
    return orders, xml_missing_warnings


def _is_didi_taxi_file(file_path):
    """判断文件是否属于滴滴出行无 XML 网约车票据。"""
    name = Path(file_path).name.lower()
    if '滴滴' in name or 'didi' in name:
        return True
    try:
        reader = PdfReader(file_path)
        text = "\n".join((page.extract_text() or "") for page in reader.pages[:1]).lower()
        return '滴滴' in text or 'didi' in text
    except Exception:
        return False


def _extract_pdf_text_for_didi_amount(pdf_path):
    """提取滴滴票据文本，供滴滴专属金额识别使用。"""
    logger = current_app.logger
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        return (text or "").replace("\x00", "")
    except Exception as e:
        logger.warning(f"使用PyMuPDF提取滴滴票据文本失败，尝试PyPDF2兜底: {e}")

    try:
        reader = PdfReader(pdf_path)
        return "\n".join((page.extract_text() or "") for page in reader.pages).replace("\x00", "")
    except Exception as e:
        logger.warning(f"使用PyPDF2提取滴滴票据文本失败: {e}")
        return ""


def _parse_chinese_money_amount(chinese_amount):
    """解析发票中文大写金额，例如：玖佰伍拾柒圆玖角整 -> 957.90。"""
    if not chinese_amount:
        return 0

    digit_map = {
        '零': 0, '〇': 0,
        '一': 1, '壹': 1,
        '二': 2, '贰': 2, '两': 2,
        '三': 3, '叁': 3,
        '四': 4, '肆': 4,
        '五': 5, '伍': 5,
        '六': 6, '陆': 6,
        '七': 7, '柒': 7,
        '八': 8, '捌': 8,
        '九': 9, '玖': 9,
    }
    unit_map = {
        '十': 10, '拾': 10,
        '百': 100, '佰': 100,
        '千': 1000, '仟': 1000,
    }

    def parse_integer_part(part):
        total = 0
        section = 0
        number = 0
        for char in part:
            if char in digit_map:
                number = digit_map[char]
            elif char in unit_map:
                if number == 0:
                    number = 1
                section += number * unit_map[char]
                number = 0
            elif char in ('万', '亿'):
                section += number
                total += section * (10000 if char == '万' else 100000000)
                section = 0
                number = 0
        return total + section + number

    normalized = chinese_amount.replace('圆', '元')
    integer_part, _, fraction_part = normalized.partition('元')
    amount = parse_integer_part(integer_part)

    jiao_match = re.search(r'([零〇一二两三四五六七八九壹贰叁肆伍陆柒捌玖])角', fraction_part)
    fen_match = re.search(r'([零〇一二两三四五六七八九壹贰叁肆伍陆柒捌玖])分', fraction_part)
    if jiao_match:
        amount += digit_map[jiao_match.group(1)] / 10
    if fen_match:
        amount += digit_map[fen_match.group(1)] / 100

    return round(amount, 2)


def _extract_didi_invoice_total_amount(invoice_path):
    """滴滴电子发票专属金额识别：优先取价税合计，而不是未税金额。"""
    logger = current_app.logger
    text = _extract_pdf_text_for_didi_amount(invoice_path)
    compact_text = re.sub(r'\s+', '', text or '')

    amount_patterns = [
        r'价税合计[（(]大写[）)][（(]小写[）)][¥￥]?(\d+\.\d{1,2})[¥￥]?',
        r'价税合计.*?[（(]小写[）)].*?[¥￥]?\s*(\d+\.\d{1,2})\s*[¥￥]?',
    ]
    for pattern in amount_patterns:
        source_text = compact_text if '\\s' not in pattern and '.*?' not in pattern else text
        match = re.search(pattern, source_text, re.DOTALL)
        if match:
            amount = round(float(match.group(1)), 2)
            logger.info(f"从滴滴电子发票价税合计提取到金额: {amount}")
            return amount

    chinese_match = re.search(
        r'价税合计.*?([零〇一二两三四五六七八九壹贰叁肆伍陆柒捌玖十拾百佰千仟万亿]+[圆元][零〇一二两三四五六七八九壹贰叁肆伍陆柒捌玖角分整]+)',
        compact_text,
        re.DOTALL
    )
    if chinese_match:
        amount = _parse_chinese_money_amount(chinese_match.group(1))
        if amount > 0:
            logger.info(f"从滴滴电子发票中文大写金额提取到金额: {amount}")
            return amount

    logger.warning(f"未能从滴滴电子发票价税合计提取金额: {invoice_path}")
    return 0


def _extract_didi_itinerary_total_amount(itinerary_path):
    """滴滴行程单专属金额识别：读取“共N笔行程，合计X元”。"""
    logger = current_app.logger
    text = _extract_pdf_text_for_didi_amount(itinerary_path)
    amount_patterns = [
        r'共\s*\d+\s*笔行程[，,]\s*合计\s*(\d+\.\d{1,2})\s*元',
        r'合计\s*(\d+\.\d{1,2})\s*元',
    ]
    for pattern in amount_patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            amount = round(float(match.group(1)), 2)
            logger.info(f"从滴滴行程单合计提取到金额: {amount}")
            return amount
    return 0


def extract_didi_taxi_amount(invoice_path, itinerary_path):
    """滴滴无 XML 两 PDF 包金额识别，限定在滴滴细分类内使用。"""
    amount = _extract_didi_invoice_total_amount(invoice_path) if invoice_path else 0
    if amount > 0:
        return amount

    amount = _extract_didi_itinerary_total_amount(itinerary_path) if itinerary_path else 0
    if amount > 0:
        return amount

    # 最后才走通用逻辑，并优先用行程单，避免发票未税金额大于价税合计时被误选。
    if itinerary_path:
        amount = extract_amount_from_pdf(itinerary_path)
        if amount > 0:
            return amount
    if invoice_path:
        return extract_amount_from_pdf(invoice_path)
    return 0


def _extract_didi_pair_key(pdf_path):
    """提取滴滴批量包内的 A/B/C 分组后缀。没有后缀时返回 default。"""
    stem = Path(pdf_path).stem.strip()
    match = re.search(r'([A-Za-z])$', stem)
    return match.group(1).upper() if match else 'default'


def _extract_didi_invoice_number(invoice_path):
    """从滴滴电子发票中提取发票号码，用于前端/session 稳定去重。"""
    text = _extract_pdf_text_for_didi_amount(invoice_path)
    match = re.search(r'发票号码[:：]\s*(\d+)', text)
    return match.group(1) if match else ''


def _pair_didi_files_by_amount(invoices, itineraries):
    """无 A/B 后缀时按金额配对滴滴发票与行程单。"""
    paired = []
    used_itinerary_indexes = set()
    itinerary_amounts = [
        (idx, _extract_didi_itinerary_total_amount(path), path)
        for idx, path in enumerate(itineraries)
    ]

    for invoice_path in invoices:
        invoice_amount = _extract_didi_invoice_total_amount(invoice_path)
        match_item = None
        for idx, itinerary_amount, itinerary_path in itinerary_amounts:
            if idx in used_itinerary_indexes:
                continue
            if invoice_amount > 0 and abs(invoice_amount - itinerary_amount) < 0.01:
                match_item = (idx, itinerary_path)
                break
        if match_item is None:
            for idx, _, itinerary_path in itinerary_amounts:
                if idx not in used_itinerary_indexes:
                    match_item = (idx, itinerary_path)
                    break
        if match_item is not None:
            used_itinerary_indexes.add(match_item[0])
            paired.append((invoice_path, match_item[1]))

    return paired


def match_didi_files_without_xml(pdf_files):
    """匹配滴滴出行的无 XML PDF 包：支持单组，也支持 A/B 多组。"""
    logger = current_app.logger
    didi_pdfs = [pdf_path for pdf_path in pdf_files if _is_didi_taxi_file(pdf_path)]
    if len(didi_pdfs) < 2:
        return {}, []

    invoices_by_key = {}
    itineraries_by_key = {}
    for pdf_path in didi_pdfs:
        pdf_type = identify_pdf_type(pdf_path)
        pair_key = _extract_didi_pair_key(pdf_path)
        if pdf_type == 'invoice':
            invoices_by_key.setdefault(pair_key, []).append(pdf_path)
        elif pdf_type == 'itinerary':
            itineraries_by_key.setdefault(pair_key, []).append(pdf_path)

    pair_keys = sorted(set(invoices_by_key) & set(itineraries_by_key))
    if not pair_keys:
        logger.info(
            f"滴滴无XML匹配条件不满足: invoices={len(invoices_by_key)}, itineraries={len(itineraries_by_key)}"
        )
        return {}, []

    orders = {}
    for pair_key in pair_keys:
        invoices = invoices_by_key[pair_key]
        itineraries = itineraries_by_key[pair_key]
        if pair_key == 'default' and (len(invoices) > 1 or len(itineraries) > 1):
            pairs = _pair_didi_files_by_amount(invoices, itineraries)
        else:
            pairs = list(zip(invoices, itineraries))

        if len(invoices) != len(itineraries):
            logger.warning(
                f"滴滴分组 {pair_key} 发票/行程单数量不一致: invoices={len(invoices)}, itineraries={len(itineraries)}"
            )

        for idx, (invoice_path, itinerary_path) in enumerate(pairs, start=1):
            amount = extract_didi_taxi_amount(invoice_path, itinerary_path)
            invoice_number = _extract_didi_invoice_number(invoice_path)
            if pair_key != 'default':
                order_id = f"滴滴出行-{pair_key}-{amount:.2f}元"
                stable_group_key = pair_key
            elif len(pairs) > 1:
                order_id = f"滴滴出行-{idx}-{amount:.2f}元"
                stable_group_key = str(idx)
            else:
                order_id = f"滴滴出行-{amount:.2f}元"
                stable_group_key = 'default'

            orders[order_id] = {
                'xml': None,
                'amount': amount,
                'didi_group_key': stable_group_key,
                'didi_invoice_number': invoice_number,
                'pdfs': {
                    'invoice': invoice_path,
                    'itinerary': itinerary_path,
                    'hotel_bill': None,
                }
            }
            logger.info(
                f"✅ 滴滴无XML票据匹配成功: order_id={order_id}, amount={amount}, group={stable_group_key}, "
                f"invoice={Path(invoice_path).name}, itinerary={Path(itinerary_path).name}"
            )
    return orders, []


def smart_match_hotel_files(orders, extract_dir):
    """智能匹配华住酒店文件"""
    logger = current_app.logger
    logger.info("🔍 开始智能匹配华住酒店文件")
    
    # 查找所有华住酒店相关文件
    hotel_invoices = []
    hotel_bills = []
    
    for order_id, order_data in orders.items():
        if order_data['pdfs']['invoice']:
            invoice_path = order_data['pdfs']['invoice']
            if 'dzfp_' in Path(invoice_path).name:
                hotel_invoices.append((order_id, invoice_path))
        
        if order_data['pdfs'].get('hotel_bill'):
            bill_path = order_data['pdfs']['hotel_bill']
            if '结账单' in Path(bill_path).name:
                hotel_bills.append((order_id, bill_path))
    
    logger.info(f"找到华住酒店发票: {len(hotel_invoices)}个")
    logger.info(f"找到华住酒店结账单: {len(hotel_bills)}个")
    
    # 如果发票和结账单数量相同，尝试匹配
    if len(hotel_invoices) == 1 and len(hotel_bills) == 1:
        invoice_order_id, invoice_path = hotel_invoices[0]
        bill_order_id, bill_path = hotel_bills[0]
        
        # 如果它们在不同的订单中，合并它们
        if invoice_order_id != bill_order_id:
            logger.info(f"🔄 合并华住酒店订单: {invoice_order_id} + {bill_order_id}")
            
            # 使用发票的订单ID作为主订单ID
            main_order_id = invoice_order_id
            main_order = orders[invoice_order_id]
            
            # 将结账单添加到主订单中
            main_order['pdfs']['hotel_bill'] = bill_path
            logger.info(f"✅ 将结账单 {Path(bill_path).name} 添加到订单 {main_order_id}")
            
            # 删除原来的结账单订单
            if bill_order_id in orders:
                del orders[bill_order_id]
                logger.info(f"🗑️ 删除重复的结账单订单: {bill_order_id}")
    
    return orders


def identify_zip_type_from_filename(zip_filename):
    """根据ZIP文件名识别类型"""
    if not zip_filename:
        return 'unknown'
    
    filename_lower = zip_filename.lower()
    
    # 检查住宿相关关键词
    hotel_keywords = [
        '华住', '酒店', 'hotel', '住宿', 'accommodation', 
        '桔子', '汉庭', '全季', '如家', '7天', '锦江',
        '结账单', '账单', 'bill'
    ]
    
    # 检查打车相关关键词
    taxi_keywords = [
        '打车', '出行', '行程', 'trip', 'itinerary',
        '高德', '滴滴', '曹操', '首汽', '阳光', 't3',
        '火箭', '及时', '约车'
    ]
    
    # 优先检查住宿关键词
    if any(keyword in filename_lower for keyword in hotel_keywords):
        return 'hotel'
    
    # 然后检查打车关键词
    if any(keyword in filename_lower for keyword in taxi_keywords):
        return 'taxi'
    
    return 'unknown'


def match_hotel_files_by_hash(pdf_files, xml_files, extract_dir):
    """使用hash前缀匹配住宿文件"""
    logger = current_app.logger
    logger.info(f"🏨 开始使用hash前缀匹配住宿文件")
    logger.info(f"PDF文件数: {len(pdf_files)}, XML文件数: {len(xml_files)}")
    
    orders = {}
    
    # 处理XML文件
    for xml_path in xml_files:
        logger.info(f"正在处理XML文件: {xml_path}")
        order_id = extract_order_id(xml_path)
        logger.info(f"从XML文件提取到订单ID: '{order_id}'")
        amount = extract_amount_from_xml(xml_path)
        
        if order_id not in orders:
            orders[order_id] = {'xml': xml_path, 'amount': amount, 'pdfs': {'invoice': None, 'itinerary': None, 'hotel_bill': None}}
            logger.info(f"创建新订单: {order_id}, 金额: {amount}")
        else:
            orders[order_id]['xml'] = xml_path
            orders[order_id]['amount'] = amount
            logger.info(f"更新订单信息: {order_id}, 金额: {amount}")
    
    # 处理PDF文件 - 使用hash前缀关联
    # 从extract_dir路径中提取hash前缀
    # 路径格式: /path/to/temp/session_id/extracted/hash_prefix/
    path_parts = Path(extract_dir).parts
    hash_prefix = None
    for part in reversed(path_parts):
        if len(part) >= 8:  # hash前缀通常是8位或更长
            hash_prefix = part
            break
    
    logger.info(f"🔑 使用hash前缀关联文件: {hash_prefix}")
    
    # 为住宿文件创建统一的订单ID
    hotel_order_id = f"hotel_{hash_prefix}" if hash_prefix else "hotel_accommodation"
    
    # 确保订单存在
    if hotel_order_id not in orders:
        orders[hotel_order_id] = {'xml': None, 'amount': 0, 'pdfs': {'invoice': None, 'itinerary': None, 'hotel_bill': None}}
        logger.info(f"创建住宿订单: {hotel_order_id}")
    
    # 将所有PDF文件按类型分类并添加到订单中，同时提取金额
    for pdf_path in pdf_files:
        logger.info(f"正在处理PDF文件: {pdf_path}")
        pdf_type = identify_pdf_type(pdf_path)
        logger.info(f"PDF文件类型: {pdf_type}")
        
        if pdf_type != 'unknown':
            orders[hotel_order_id]['pdfs'][pdf_type] = pdf_path
            logger.info(f"为住宿订单 {hotel_order_id} 添加 {pdf_type} 类型的PDF: {pdf_path}")
            
            # 如果是酒店发票，尝试从PDF中提取金额
            if pdf_type == 'invoice' and orders[hotel_order_id]['amount'] == 0:
                pdf_amount = extract_amount_from_pdf(pdf_path)
                if pdf_amount > 0:
                    orders[hotel_order_id]['amount'] = pdf_amount
                    logger.info(f"🏨 从酒店发票PDF中提取到金额: {pdf_amount}")
    
    # 检查所有订单的金额状态（针对酒店文件）
    amount_warnings = []
    for order_id, order_data in orders.items():
        if order_data['xml'] is None and order_data['amount'] == 0:
            # 酒店文件没有XML，也没有从PDF提取到金额
            amount_warnings.append({
                'order_id': order_id,
                'reason': '酒店发票金额提取失败',
                'impact': '无法获取金额信息，请检查发票文件',
                'type': 'hotel'
            })
            logger.warning(f"⚠️ 酒店订单 {order_id} 无法提取金额信息")
        elif order_data['xml'] is None and order_data['amount'] > 0:
            # 酒店文件没有XML，但成功从PDF提取到金额
            logger.info(f"✅ 酒店订单 {order_id} 从PDF成功提取金额: {order_data['amount']}")
        elif order_data['xml'] is not None and order_data['amount'] == 0:
            # 有XML但金额为0（这种情况在酒店文件中较少见）
            amount_warnings.append({
                'order_id': order_id,
                'reason': 'XML中未找到金额信息',
                'impact': '金额统计为0，可能不准确',
                'type': 'hotel'
            })
            logger.warning(f"⚠️ 酒店订单 {order_id} XML中未找到金额信息")
    
    logger.info(f"🏨 住宿文件匹配完成，共找到 {len(orders)} 个订单，金额警告: {len(amount_warnings)} 个")
    return orders, amount_warnings




def create_smart_combined_pdf(itinerary_path: str, invoice_path: str, output_path: str, page_count: int = 1) -> bool:
    """
    创建智能拼接PDF - 统一处理1页和多页行程单的拼接逻辑
    
    Args:
        itinerary_path: 行程单文件路径
        invoice_path: 发票文件路径  
        output_path: 输出文件路径
        page_count: 行程单页数，1表示单页，>1表示多页
    
    Returns:
        bool: 拼接是否成功
    """
    logger = current_app.logger
    logger.info(f"开始智能拼接PDF，行程单页数: {page_count}")
    
    try:
        if page_count == 1:
            # 单页行程单：发票在上，行程单在下，压缩到一页
            logger.info("🔄 处理单页行程单：发票在上 + 行程单在下，压缩到一页")
            return create_smart_combined_single_page(itinerary_path, invoice_path, output_path)
        else:
            # 多页行程单：生成完整的拼接文件
            # 第一页：发票+行程单第一页内容
            # 后续页面：行程单的剩余页面
            logger.info("🔄 处理多页行程单：生成完整的拼接文件（发票+行程单所有页面）")
            return create_smart_combined_multi_page(itinerary_path, invoice_path, output_path, page_count)
            
    except Exception as e:
        logger.error(f"❌ 智能拼接PDF失败: {e}")
        return False


def _box_size_and_origin(box):
    """返回 PDF 页面盒子的尺寸和原点，兼容 PyPDF2 的 RectangleObject。"""
    left = float(box.left)
    bottom = float(box.bottom)
    right = float(box.right)
    top = float(box.top)
    return right - left, top - bottom, left, bottom


def _should_render_invoice_with_cropbox(invoice_path: str) -> bool:
    """判断发票是否需要按 CropBox 渲染，避免把不可见空白外框拼进结果。"""
    logger = current_app.logger
    try:
        reader = PdfReader(invoice_path)
        if not reader.pages:
            return False

        page = reader.pages[0]
        media_w, media_h, media_left, media_bottom = _box_size_and_origin(page.mediabox)
        crop_w, crop_h, crop_left, crop_bottom = _box_size_and_origin(page.cropbox)
        if media_w <= 0 or media_h <= 0 or crop_w <= 0 or crop_h <= 0:
            return False

        media_area = media_w * media_h
        crop_area = crop_w * crop_h
        area_ratio = crop_area / media_area
        dimension_delta = max(abs(media_w - crop_w) / media_w, abs(media_h - crop_h) / media_h)
        origin_delta = max(abs(media_left - crop_left), abs(media_bottom - crop_bottom))
        use_cropbox = area_ratio < 0.98 or dimension_delta > 0.02 or origin_delta > 1.0

        logger.info(
            "发票页面盒检测: media=(%.2f x %.2f @ %.2f,%.2f), "
            "crop=(%.2f x %.2f @ %.2f,%.2f), area_ratio=%.3f, use_cropbox=%s",
            media_w, media_h, media_left, media_bottom,
            crop_w, crop_h, crop_left, crop_bottom,
            area_ratio, use_cropbox,
        )
        return use_cropbox
    except Exception as e:
        logger.warning(f"发票页面盒检测失败，使用默认渲染: {e}")
        return False


def _render_invoice_images(invoice_path: str, dpi: int = 300):
    """渲染发票图片；当 PDF 有有效 CropBox 时使用可见区域，保持普通发票兼容。"""
    from pdf2image import convert_from_path

    use_cropbox = _should_render_invoice_with_cropbox(invoice_path)
    return convert_from_path(invoice_path, dpi=dpi, use_cropbox=use_cropbox)


def _find_itinerary_table_crop_box(itinerary_path, image_size):
    """根据行程单抬头和表格边界返回图片裁剪框，保留汇总信息和完整表格。"""
    logger = current_app.logger
    try:
        import pdfplumber
    except ImportError:
        logger.warning("未安装 pdfplumber，行程单裁剪使用旧逻辑")
        return None

    try:
        with pdfplumber.open(itinerary_path) as pdf:
            if not pdf.pages:
                return None
            page = pdf.pages[0]
            tables = page.find_tables(table_settings={
                "vertical_strategy": "lines",
                "horizontal_strategy": "lines",
            })
            if not tables:
                return None

            table = max(tables, key=lambda t: (t.bbox[2] - t.bbox[0]) * (t.bbox[3] - t.bbox[1]))
            x0, top, x1, bottom = table.bbox
            img_w, img_h = image_size
            scale_x = img_w / float(page.width)
            scale_y = img_h / float(page.height)

            words = page.extract_words() or []
            header_tops = [
                word["top"]
                for word in words
                if any(keyword in word.get("text", "") for keyword in ("滴滴出行", "申请日期", "行程起止日期", "行程人手机号", "合计"))
            ]
            header_top = min(header_tops) if header_tops else max(0, top - 160)
            # 留出一点页眉空白，避免“滴滴出行-行程单”等抬头被贴边裁掉。
            crop_top = max(0, int(header_top * scale_y - 18 * scale_y))

            pad_bottom = 24 * scale_y
            crop_box = (
                0,
                crop_top,
                img_w,
                min(img_h, int(bottom * scale_y + pad_bottom)),
            )
            logger.info(
                f"✂️ 基于抬头+表格边界裁剪行程单: header_top={header_top:.2f}, "
                f"pdf_table_bbox={table.bbox}, image_crop={crop_box}"
            )
            return crop_box
    except Exception as e:
        logger.warning(f"基于表格边界计算行程单裁剪区域失败: {e}")
        return None


def _fit_image_to_box(image, box_width, box_height):
    """等比缩放图片到指定区域内，避免裁剪内容。"""
    from PIL import Image

    ratio = min(box_width / image.width, box_height / image.height)
    resized = image.resize(
        (max(1, int(image.width * ratio)), max(1, int(image.height * ratio))),
        Image.Resampling.LANCZOS,
    )
    canvas = Image.new("RGB", (box_width, box_height), (255, 255, 255))
    paste_x = (box_width - resized.width) // 2
    paste_y = (box_height - resized.height) // 2
    canvas.paste(resized, (paste_x, paste_y))
    return canvas


def create_smart_combined_single_page(itinerary_path: str, invoice_path: str, output_path: str) -> bool:
    """
    创建单页智能拼接：发票在上（占50%高度），行程单在下（占50%高度），压缩到一页
    
    采用图片拼接方式，更加稳定可靠，避免PDF工具拼接的黑色区域问题
    """
    logger = current_app.logger
    logger.info(f"🚀 开始创建单页智能拼接：发票在上（50%）+ 行程单在下（50%），压缩到一页")
    
    try:
        # 导入必要的库
        try:
            from pdf2image import convert_from_path
            from PIL import Image
        except ImportError as e:
            logger.error(f"❌ 缺少必要的库: {e}")
            logger.info("请安装: pip install pdf2image Pillow")
            return False
        
        # 从文件名中匹配发票/行程单中包含的行程数量
        # 实例文件名：【阳光出行-32.13元-3个行程】高德打车电子发票，匹配其中的3个行程
        itinerary_name = Path(itinerary_path).name
        invoice_name = Path(invoice_path).name
        itinerary_match = re.search(r'-(\d+)个行程', itinerary_name)
        invoice_match = re.search(r'-(\d+)个行程', invoice_name)
        itinerary_count = int(itinerary_match.group(1)) if itinerary_match else 1
        invoice_count = int(invoice_match.group(1)) if invoice_match else 1
        
        # 验证行程数量一致性
        if itinerary_count != invoice_count:
            logger.warning(f"⚠️ 行程单和发票的行程数量不一致：行程单{itinerary_count}个，发票{invoice_count}个")
            logger.info("使用行程单的数量作为标准")
            itinerary_count = max(itinerary_count, invoice_count)
        
        logger.info(f"📊 检测到行程数量: {itinerary_count}个")
        
        # A4尺寸（像素，300 DPI）
        A4_WIDTH, A4_HEIGHT = 2480, 3508
        # 定义页边距（像素）
        MARGIN = 100
        # 考虑页边距后的实际可用宽度和高度
        USABLE_WIDTH = A4_WIDTH - 2 * MARGIN
        USABLE_HEIGHT = A4_HEIGHT - 2 * MARGIN
        
        # 计算每个行程的高度比例
        per_count_height = USABLE_HEIGHT / 21
        
        try:
            # 转换行程单为图片
            logger.info("📄 转换行程单为图片")
            itinerary_images = convert_from_path(itinerary_path, dpi=300)
            itinerary_image = itinerary_images[0]
            w, h = itinerary_image.size

            crop_box = _find_itinerary_table_crop_box(itinerary_path, (w, h))
            if crop_box:
                itinerary_part = itinerary_image.crop(crop_box)
            else:
                # 兜底：去掉页眉后保留到页尾，再缩印到下半页，避免多行程被截断。
                crop_top = int(4 * per_count_height)
                crop_bottom = h
                itinerary_part = itinerary_image.crop((0, crop_top, w, crop_bottom))
                logger.info(f"✂️ 行程单兜底裁剪区域: 顶部{crop_top}px, 底部{crop_bottom}px")

            itinerary_part = _fit_image_to_box(
                itinerary_part.convert("RGB"),
                USABLE_WIDTH,
                int(USABLE_HEIGHT * 0.5),
            )
            
            # 转换发票为图片
            logger.info("🧾 转换发票为图片")
            invoice_images = _render_invoice_images(invoice_path, dpi=300)
            invoice_image = invoice_images[0]
            
            # 调整发票尺寸（占上半部分，50%高度）
            ratio = USABLE_WIDTH / invoice_image.width
            new_size = (USABLE_WIDTH, int(USABLE_HEIGHT * 0.5))
            invoice_image = invoice_image.resize(new_size, Image.Resampling.LANCZOS)
            
            # 创建新的空白图片
            combined = Image.new("RGB", (A4_WIDTH, A4_HEIGHT), (255, 255, 255))
            
            # 粘贴发票到上半部分（考虑页边距）
            combined.paste(invoice_image, (MARGIN, MARGIN))
            
            # 粘贴行程单到下半部分（考虑页边距）
            combined.paste(itinerary_part, (MARGIN, MARGIN + invoice_image.height))
            
            # 最后再缩放到A4纸
            combined = combined.resize((A4_WIDTH, A4_HEIGHT), Image.Resampling.LANCZOS)
            
            # 保存为PDF
            logger.info("💾 保存拼接后的图片为PDF")
            combined.save(output_path, "PDF", resolution=300.0)
            
            # 验证输出文件
            if Path(output_path).exists():
                file_size = Path(output_path).stat().st_size
                logger.info(f"📊 单页拼接文件大小: {file_size} bytes")
                
                # 验证文件质量
                if file_size < 1000:
                    logger.error("❌ 拼接文件过小，可能拼接失败")
                    return False
                
                logger.info("✅ 单页智能拼接成功（发票+行程单图片拼接到一页）")
                logger.info(f"   文件路径: {output_path}")
                logger.info(f"   文件大小: {file_size} bytes")
                return True
            else:
                logger.error("❌ 单页拼接输出文件未生成")
                return False
                
        except Exception as e:
            logger.error(f"❌ 图片拼接过程中出错: {str(e)}")
            raise
            
    except Exception as e:
        logger.error(f"❌ 创建单页智能拼接失败: {e}")
        return False


def create_smart_combined_multi_page(itinerary_path: str, invoice_path: str, output_path: str, page_count: int) -> bool:
    """
    创建多页智能拼接：生成完整的拼接文件
    
    第一页：发票+行程单第一页内容
    后续页面：行程单的剩余页面（第2页、第3页...）
    
    这样预览时可以看到完整内容，打印时也能正确处理
    """
    logger = current_app.logger
    try:
        logger.info(f"🚀 开始创建多页智能拼接，行程单总页数: {page_count}")
        
        # 检查是否有必要的工具
        import subprocess
        import shutil
        if not shutil.which('pdftk'):
            logger.warning("未找到pdftk工具，改用图片方式生成多页拼接PDF")
            return create_smart_combined_multi_page_image(itinerary_path, invoice_path, output_path, page_count)
        
        # 创建临时文件
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_invoice_first = Path(temp_dir) / f"temp_invoice_first_{uuid.uuid4().hex[:8]}.pdf"
        temp_itinerary_first = Path(temp_dir) / f"temp_itinerary_first_{uuid.uuid4().hex[:8]}.pdf"
        temp_remaining_pages = Path(temp_dir) / f"temp_remaining_{uuid.uuid4().hex[:8]}.pdf"
        
        try:
            # 1. 提取发票第一页
            logger.info("🧾 提取发票第一页")
            subprocess.run(['pdftk', invoice_path, 'cat', '1', 'output', temp_invoice_first], check=True)
            
            # 2. 提取行程单第一页
            logger.info("📄 提取行程单第一页")
            subprocess.run(['pdftk', itinerary_path, 'cat', '1', 'output', temp_itinerary_first], check=True)
            
            # 3. 提取行程单剩余页面（第2页到最后一页）
            if page_count > 1:
                logger.info(f"📄 提取行程单剩余页面（第2页到第{page_count}页）")
                subprocess.run(['pdftk', itinerary_path, 'cat', '2-end', 'output', temp_remaining_pages], check=True)
            
            # 4. 拼接第一页：发票+行程单第一页内容
            logger.info("🔗 拼接第一页：发票在上 + 行程单第一页内容")
            first_page_combined = Path(temp_dir) / f"first_page_combined_{uuid.uuid4().hex[:8]}.pdf"
            
            subprocess.run([
                'pdftk', temp_invoice_first, temp_itinerary_first, 
                'cat', 'output', first_page_combined
            ], check=True)
            
            # 5. 合并所有页面
            logger.info("🔗 合并所有页面：第一页（发票+行程单第一页）+ 剩余页面")
            
            if page_count > 1:
                # 多页：第一页拼接 + 剩余页面
                subprocess.run([
                    'pdftk', first_page_combined, temp_remaining_pages, 
                    'cat', 'output', output_path
                ], check=True)
            else:
                # 单页：直接使用第一页拼接结果
                import shutil
                shutil.copy2(first_page_combined, output_path)
            
            # 验证输出文件
            if Path(output_path).exists():
                file_size = Path(output_path).stat().st_size
                logger.info(f"📊 多页拼接文件大小: {file_size} bytes")
                
                # 验证文件质量
                if file_size < 1000:
                    logger.warning("⚠️ 拼接文件过小，可能拼接失败")
                    return False
                
                # 验证PDF页数
                result = subprocess.run(['pdftk', output_path, 'dump_data'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    output_page_count = 0
                    for line in result.stdout.split('\n'):
                        if line.startswith('NumberOfPages:'):
                            output_page_count = int(line.split(':')[1].strip())
                            break
                    
                    expected_pages = 1 + page_count  # 1页（发票+行程单第一页）+ 行程单剩余页面
                    if output_page_count == expected_pages:
                        logger.info(f"✅ 多页拼接成功：{output_page_count}页")
                        logger.info(f"   文件路径: {output_path}")
                        logger.info(f"   文件大小: {file_size} bytes")
                        logger.info(f"   预期页数: {expected_pages}页")
                        return True
                    else:
                        logger.warning(f"⚠️ 页数不匹配：实际{output_page_count}页，预期{expected_pages}页")
                        return False
                        
                else:
                    logger.warning("⚠️ 无法验证PDF页数")
                    return False
                    
            else:
                logger.error("❌ 输出文件创建失败")
                return False
                
        finally:
            # 清理临时文件
            temp_files = [temp_invoice_first, temp_itinerary_first, temp_remaining_pages, first_page_combined]
            for temp_file in temp_files:
                if Path(temp_file).exists():
                    try:
                        Path(temp_file).unlink()
                    except Exception as e:
                        logger.warning(f"清理临时文件失败: {temp_file}, 错误: {e}")
        
    except Exception as e:
        logger.error(f"❌ 创建多页智能拼接失败: {e}")
        return False




def create_smart_combined_multi_page_image(itinerary_path: str, invoice_path: str, output_path: str, page_count: int) -> bool:
    """不依赖 pdftk 的多页网约车拼接兜底：第一页发票+行程单，后续页保留行程单。"""
    logger = current_app.logger
    try:
        from pdf2image import convert_from_path
        from PIL import Image
    except ImportError as e:
        logger.error(f"❌ 缺少多页图片拼接依赖: {e}")
        return False

    try:
        A4_WIDTH, A4_HEIGHT = 2480, 3508
        MARGIN = 100
        USABLE_WIDTH = A4_WIDTH - 2 * MARGIN
        USABLE_HEIGHT = A4_HEIGHT - 2 * MARGIN
        per_count_height = USABLE_HEIGHT / 21

        itinerary_name = Path(itinerary_path).name
        invoice_name = Path(invoice_path).name
        itinerary_match = re.search(r'-(\d+)个行程', itinerary_name)
        invoice_match = re.search(r'-(\d+)个行程', invoice_name)
        itinerary_count = int(itinerary_match.group(1)) if itinerary_match else 1
        if invoice_match:
            itinerary_count = max(itinerary_count, int(invoice_match.group(1)))

        logger.info("📄 图片方式转换多页行程单")
        itinerary_images = convert_from_path(itinerary_path, dpi=300)
        if not itinerary_images:
            logger.error("❌ 多页行程单渲染为空")
            return False

        first_itinerary = itinerary_images[0].convert("RGB")
        w, h = first_itinerary.size
        crop_top = int(4 * per_count_height)
        crop_bottom = int(h // 2 + per_count_height * (itinerary_count - 1))
        first_itinerary_part = first_itinerary.crop((0, crop_top, w, min(h, crop_bottom)))
        first_itinerary_part = first_itinerary_part.resize(
            (USABLE_WIDTH, int(USABLE_HEIGHT * 0.5)),
            Image.Resampling.LANCZOS,
        )

        logger.info("🧾 图片方式转换发票")
        invoice_images = _render_invoice_images(invoice_path, dpi=300)
        if not invoice_images:
            logger.error("❌ 发票渲染为空")
            return False
        invoice_image = invoice_images[0].convert("RGB").resize(
            (USABLE_WIDTH, int(USABLE_HEIGHT * 0.5)),
            Image.Resampling.LANCZOS,
        )

        pages = []
        first_page = Image.new("RGB", (A4_WIDTH, A4_HEIGHT), (255, 255, 255))
        first_page.paste(invoice_image, (MARGIN, MARGIN))
        first_page.paste(first_itinerary_part, (MARGIN, MARGIN + invoice_image.height))
        pages.append(first_page)

        for page_image in itinerary_images[1:]:
            page_image = page_image.convert("RGB")
            ratio = min(USABLE_WIDTH / page_image.width, USABLE_HEIGHT / page_image.height)
            resized = page_image.resize(
                (max(1, int(page_image.width * ratio)), max(1, int(page_image.height * ratio))),
                Image.Resampling.LANCZOS,
            )
            page = Image.new("RGB", (A4_WIDTH, A4_HEIGHT), (255, 255, 255))
            x = (A4_WIDTH - resized.width) // 2
            y = (A4_HEIGHT - resized.height) // 2
            page.paste(resized, (x, y))
            pages.append(page)

        pages[0].save(
            output_path,
            "PDF",
            resolution=300.0,
            save_all=len(pages) > 1,
            append_images=pages[1:],
        )
        if not Path(output_path).exists() or Path(output_path).stat().st_size < 1000:
            logger.error(f"❌ 图片方式多页拼接输出异常: {output_path}")
            return False

        logger.info(f"✅ 图片方式多页拼接成功: {output_path}, pages={len(pages)}")
        return True
    except Exception as e:
        logger.error(f"❌ 图片方式多页拼接失败: {e}", exc_info=True)
        return False


def create_hotel_combined_pdf(invoice_path: str, hotel_bill_path: str, output_path: str) -> bool:
    """创建住宿发票+结账单的拼接页面：发票完整占上半页，结账单上部占下半页。"""
    logger = current_app.logger
    try:
        logger.info(f"🏨 开始创建住宿拼接页面：发票完整上半页 + 结账单上部下半页")
        logger.info(f"   发票文件: {Path(invoice_path).name}")
        logger.info(f"   结账单文件: {Path(hotel_bill_path).name}")
        
        # 导入必要的库
        try:
            from pdf2image import convert_from_path
            from PIL import Image
        except ImportError as e:
            logger.error(f"❌ 缺少必要的库: {e}")
            logger.info("请安装: pip install pdf2image Pillow")
            return False
        
        # A4尺寸（像素，300 DPI）
        A4_WIDTH, A4_HEIGHT = 2480, 3508
        # 定义页边距（像素）
        MARGIN = 100
        # 考虑页边距后的实际可用宽度和高度
        USABLE_WIDTH = A4_WIDTH - 2 * MARGIN
        USABLE_HEIGHT = A4_HEIGHT - 2 * MARGIN
        
        try:
            # 1. 转换结账单为图片
            logger.info("📄 转换结账单为图片")
            bill_images = convert_from_path(hotel_bill_path, dpi=300)
            bill_image = bill_images[0]
            w, h = bill_image.size
            
            # 2. 提取结账单上部50%（修复：确保是上部而不是下部）
            logger.info("✂️ 提取结账单上部50%")
            # 上部50%：从顶部(0)到中间(h//2)
            top_half = bill_image.crop((0, 0, w, h // 2))
            logger.info(f"✂️ 结账单裁剪区域: 顶部0px, 底部{h//2}px")
            
            # 3. 调整结账单尺寸（占下半部分，50%高度）
            ratio = USABLE_WIDTH / top_half.width
            new_size = (USABLE_WIDTH, int(USABLE_HEIGHT * 0.5))
            top_half = top_half.resize(new_size, Image.Resampling.LANCZOS)
            
            # 4. 转换发票为图片
            logger.info("🧾 转换发票为图片")
            invoice_images = _render_invoice_images(invoice_path, dpi=300)
            invoice_image = invoice_images[0]
            
            # 5. 调整发票尺寸（完整占上半部分，50%高度），保持与网约车发票相同的半页标准。
            ratio = USABLE_WIDTH / invoice_image.width
            new_size = (USABLE_WIDTH, int(USABLE_HEIGHT * 0.5))
            invoice_image = invoice_image.resize(new_size, Image.Resampling.LANCZOS)
            
            # 6. 创建新的空白图片
            combined = Image.new("RGB", (A4_WIDTH, A4_HEIGHT), (255, 255, 255))
            
            # 7. 粘贴发票到上半部分（考虑页边距）
            combined.paste(invoice_image, (MARGIN, MARGIN))
            
            # 8. 粘贴结账单上部到下半部分（考虑页边距）
            combined.paste(top_half, (MARGIN, MARGIN + invoice_image.height))
            
            # 9. 最后再缩放到A4纸
            combined = combined.resize((A4_WIDTH, A4_HEIGHT), Image.Resampling.LANCZOS)
            
            # 10. 保存为PDF
            logger.info("💾 保存拼接后的图片为PDF")
            combined.save(output_path, "PDF", resolution=300.0)
            
            # 验证输出文件
            if Path(output_path).exists():
                file_size = Path(output_path).stat().st_size
                logger.info(f"📊 住宿拼接文件大小: {file_size} bytes")
                
                # 验证文件质量
                if file_size < 1000:
                    logger.error("❌ 拼接文件过小，可能拼接失败")
                    return False
                
                logger.info("✅ 住宿拼接成功（发票完整上半页 + 结账单上部下半页）")
                logger.info(f"   文件路径: {output_path}")
                logger.info(f"   文件大小: {file_size} bytes")
                return True
            else:
                logger.error("❌ 住宿拼接输出文件未生成")
                return False
                
        except Exception as e:
            logger.error(f"❌ 图片拼接过程中出错: {str(e)}")
            raise
        
    except Exception as e:
        logger.error(f"❌ 创建住宿拼接页面失败: {e}")
        return False


def _extract_train_amount_from_text(text):
    """从火车票文本中提取票面金额。"""
    if not text:
        return 0.0

    patterns = [
        r"[¥￥]\s*(\d+\.\d{1,2})",
        r"票价[：:\s]*([0-9]+\.[0-9]{1,2})",
        r"票面金额[：:\s]*([0-9]+\.[0-9]{1,2})",
        r"价税合计[：:\s]*([0-9]+\.[0-9]{1,2})",
        r"(\d+\.\d{1,2})\s*元",
        r"(\d+\.\d{1,2})",
    ]
    candidates = []
    for p in patterns:
        for m in re.findall(p, text, flags=re.IGNORECASE):
            try:
                value = float(m)
            except Exception:
                continue
            if 1 <= value <= 10000:
                candidates.append(value)
    return max(candidates) if candidates else 0.0


def _extract_train_meta_from_text(text, source_name):
    """提取火车票基础信息：车次、起终点（尽力而为）。"""
    if not text:
        return {"train_no": "", "from_station": "", "to_station": "", "display_name": Path(source_name).stem}

    train_no = ""
    m_no = re.search(r"\b([GDCZTK]\d{1,4})\b", text, flags=re.IGNORECASE)
    if m_no:
        train_no = m_no.group(1).upper()

    from_station = ""
    to_station = ""

    # 英文站名兜底：如 HuashanbeiG1896 ... Hangzhoudong
    m_from = re.search(r"\b([A-Za-z]{3,})\s*[GDCZTK]\d{1,4}\b", text)
    if m_from:
        from_station = m_from.group(1)

    if train_no:
        m_to = re.search(rf"\b{re.escape(train_no)}\b.*?\b([A-Za-z]{{3,}})\b", text, flags=re.IGNORECASE | re.DOTALL)
        if m_to:
            to_station = m_to.group(1)

    display_name = Path(source_name).stem
    if train_no:
        display_name = f"{display_name}-{train_no}"
    if from_station and to_station and from_station.lower() != to_station.lower():
        display_name = f"{display_name} ({from_station}→{to_station})"

    return {
        "train_no": train_no,
        "from_station": from_station,
        "to_station": to_station,
        "display_name": display_name,
    }


def _extract_flight_meta_from_text(text, source_name):
    """提取机票基础信息：航班号、起终点（尽力而为）。"""
    display_name = Path(source_name).stem
    if not text:
        return {"flight_no": "", "from_station": "", "to_station": "", "display_name": display_name}

    flight_no = ""
    m_no = re.search(r"\b([A-Z]{2}\d{3,4})\b", text, flags=re.IGNORECASE)
    if m_no:
        flight_no = m_no.group(1).upper()

    from_station = ""
    to_station = ""
    route_match = re.search(r"([\u4e00-\u9fa5A-Za-z]{2,})\s*[-—→]\s*([\u4e00-\u9fa5A-Za-z]{2,})", text)
    if route_match:
        from_station = route_match.group(1).strip()
        to_station = route_match.group(2).strip()

    if flight_no:
        display_name = f"{display_name}-{flight_no}"
    if from_station and to_station and from_station.lower() != to_station.lower():
        display_name = f"{display_name} ({from_station}→{to_station})"

    return {
        "flight_no": flight_no,
        "from_station": from_station,
        "to_station": to_station,
        "display_name": display_name,
    }


def _collect_train_ticket_pages(train_ticket_pdfs):
    """
    收集火车票页面级数据（每页视作一张票），并提取每页金额。
    返回 list[dict(pdf_path, page_no, amount, source_name)]。
    """
    logger = current_app.logger
    pages = []
    try:
        import fitz
        use_fitz = True
    except Exception:
        use_fitz = False

    for ticket_pdf in sorted(train_ticket_pdfs, key=lambda p: Path(p[0] if isinstance(p, (tuple, list)) else p).name):
        if isinstance(ticket_pdf, (tuple, list)):
            pdf_path, ticket_type = ticket_pdf[0], ticket_pdf[1]
        else:
            pdf_path = ticket_pdf
            ticket_type = identify_pdf_type(pdf_path)
        is_flight = ticket_type == 'flight_ticket'
        try:
            if use_fitz:
                doc = fitz.open(pdf_path)
                for i in range(len(doc)):
                    text = doc.load_page(i).get_text() or ""
                    amount = _extract_train_amount_from_text(text)
                    meta = _extract_flight_meta_from_text(text, Path(pdf_path).name) if is_flight else _extract_train_meta_from_text(text, Path(pdf_path).name)
                    pages.append({
                        "pdf_path": pdf_path,
                        "page_no": i + 1,
                        "amount": amount,
                        "source_name": Path(pdf_path).name,
                        "ticket_type": "flight" if is_flight else "train",
                        "train_no": meta.get("train_no", ""),
                        "flight_no": meta.get("flight_no", ""),
                        "from_station": meta["from_station"],
                        "to_station": meta["to_station"],
                        "display_name": meta["display_name"],
                    })
                doc.close()
            else:
                reader = PdfReader(pdf_path)
                for i, page in enumerate(reader.pages):
                    text = page.extract_text() or ""
                    amount = _extract_train_amount_from_text(text)
                    meta = _extract_flight_meta_from_text(text, Path(pdf_path).name) if is_flight else _extract_train_meta_from_text(text, Path(pdf_path).name)
                    pages.append({
                        "pdf_path": pdf_path,
                        "page_no": i + 1,
                        "amount": amount,
                        "source_name": Path(pdf_path).name,
                        "ticket_type": "flight" if is_flight else "train",
                        "train_no": meta.get("train_no", ""),
                        "flight_no": meta.get("flight_no", ""),
                        "from_station": meta["from_station"],
                        "to_station": meta["to_station"],
                        "display_name": meta["display_name"],
                    })
        except Exception as e:
            logger.warning(f"火车票页面解析失败: {pdf_path}, err={e}")

    return pages


def _split_train_ticket_groups(train_ticket_items):
    """
    火车票分页规则（最新业务）：
    - 每页最多 2 张（上下排）
    - 1 张票 -> 1 页（单票）
    - 2 张票 -> 1 页（上下排）
    - 3 张票 -> 第1页2张 + 第2页1张
    - N 张票 -> 按 2 张一页拆分，最后可能剩 1 张
    """
    def _sort_index(value, default_index):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default_index

    # 不能按文件名重新排序，否则会覆盖用户在前端拖拽后的拼接顺序。
    # 没有显式排序字段时保持调用方传入顺序，避免破坏上传/增量顺序。
    sorted_items = [
        item for _, item in sorted(
            enumerate(train_ticket_items),
            key=lambda pair: (_sort_index(pair[1].get("train_sort_index"), pair[0]), pair[0])
        )
    ]
    groups = []
    i = 0
    while i < len(sorted_items):
        remaining = len(sorted_items) - i
        take = 2 if remaining >= 2 else 1
        groups.append(sorted_items[i:i + take])
        i += take
    return groups


def create_train_ticket_layout_pdf(train_ticket_items, output_path):
    """将火车票按数量智能排版到 A4 页面。"""
    logger = current_app.logger
    ticket_count = len(train_ticket_items)
    if ticket_count == 0:
        return False

    try:
        from pdf2image import convert_from_path
        from PIL import Image
    except ImportError as e:
        logger.error(f"❌ 缺少火车票排版依赖: {e}")
        logger.info("请安装: pip install pdf2image Pillow")
        return False

    # A4 300DPI
    A4_WIDTH, A4_HEIGHT = 2480, 3508
    PAGE_MARGIN = 80
    CELL_GAP = 40

    if ticket_count == 1:
        rows, cols = 1, 1
        layout_type = "train_single"
    elif ticket_count == 2:
        rows, cols = 2, 1
        layout_type = "train_double"
    else:
        # 业务上限：每页最多2张。兜底保护，避免错误输入导致2x2。
        rows, cols = 2, 1
        layout_type = "train_double_fallback"

    cell_width = (A4_WIDTH - 2 * PAGE_MARGIN - (cols - 1) * CELL_GAP) // cols
    cell_height = (A4_HEIGHT - 2 * PAGE_MARGIN - (rows - 1) * CELL_GAP) // rows
    canvas = Image.new("RGB", (A4_WIDTH, A4_HEIGHT), (255, 255, 255))

    logger.info(f"🚆 火车票排版开始: tickets={ticket_count}, layout={layout_type}")

    for idx, ticket_item in enumerate(train_ticket_items):
        try:
            ticket_path = ticket_item["pdf_path"]
            page_no = ticket_item["page_no"]
            images = convert_from_path(ticket_path, dpi=220, first_page=page_no, last_page=page_no)
            if not images:
                logger.warning(f"火车票渲染为空: {ticket_path}#p{page_no}")
                continue
            ticket_img = images[0].convert("RGB")
        except Exception as e:
            logger.error(f"火车票渲染失败: {ticket_path}, err={e}")
            continue

        row = idx // cols
        col = idx % cols
        if row >= rows:
            # 理论上不会超过，因为分组已控制
            break

        # 按单元格等比缩放
        ratio = min(cell_width / ticket_img.width, cell_height / ticket_img.height)
        resized = ticket_img.resize(
            (max(1, int(ticket_img.width * ratio)), max(1, int(ticket_img.height * ratio))),
            Image.Resampling.LANCZOS,
        )

        cell_x = PAGE_MARGIN + col * (cell_width + CELL_GAP)
        cell_y = PAGE_MARGIN + row * (cell_height + CELL_GAP)
        paste_x = cell_x + (cell_width - resized.width) // 2
        paste_y = cell_y + (cell_height - resized.height) // 2
        canvas.paste(resized, (paste_x, paste_y))

    canvas.save(output_path, "PDF", resolution=300.0)
    if not Path(output_path).exists() or Path(output_path).stat().st_size < 1000:
        logger.error(f"❌ 火车票排版输出异常: {output_path}")
        return False

    logger.info(f"✅ 火车票排版成功: {output_path}")
    return True


def process_pdf_files(extract_dir, zip_filename=None):
    """处理解压后的PDF和XML文件"""
    logger = current_app.logger
    logger.info(f"开始处理解压后的文件: {extract_dir}")
    
    # 根据ZIP文件名判断处理类型
    zip_type = identify_zip_type_from_filename(zip_filename) if zip_filename else 'unknown'
    logger.info(f"ZIP文件类型: {zip_type}")
    
    # 获取所有文件路径
    file_paths = get_file_paths(extract_dir)
    grouped_files = group_files_by_type(file_paths)

    # 先识别交通票据（火车票/机票），避免与网约车/酒店混淆
    transport_ticket_pdfs = []
    non_train_pdfs = []
    for pdf_path in grouped_files['pdf']:
        pdf_type = identify_pdf_type(pdf_path)
        if pdf_type in ('train_ticket', 'flight_ticket'):
            transport_ticket_pdfs.append((pdf_path, pdf_type))
        else:
            non_train_pdfs.append(pdf_path)

    if transport_ticket_pdfs:
        train_pdf_count = sum(1 for _, t in transport_ticket_pdfs if t == 'train_ticket')
        flight_pdf_count = sum(1 for _, t in transport_ticket_pdfs if t == 'flight_ticket')
        logger.info(f"🚆✈️ 识别到交通票据文件 {len(transport_ticket_pdfs)} 个(火车{train_pdf_count}, 机票{flight_pdf_count})")
    if non_train_pdfs:
        logger.info(f"🚗/🏨 非火车票 PDF 文件 {len(non_train_pdfs)} 个")

    non_train_grouped = {
        'pdf': non_train_pdfs,
        'xml': grouped_files['xml'],
        'other': grouped_files['other'],
    }

    # 根据ZIP类型选择不同的处理策略
    if zip_type == 'hotel':
        # 住宿记录：使用hash前缀关联文件
        orders, xml_missing_warnings = match_hotel_files_by_hash(non_train_grouped['pdf'], non_train_grouped['xml'], extract_dir)
    else:
        # 打车行程单：滴滴无XML两PDF包优先按同一订单匹配，否则使用通用订单匹配逻辑
        if zip_type == 'taxi' and not non_train_grouped['xml']:
            orders, xml_missing_warnings = match_didi_files_without_xml(non_train_grouped['pdf'])
            if not orders:
                orders, xml_missing_warnings = match_files_by_order(non_train_grouped['pdf'], non_train_grouped['xml'])
        else:
            orders, xml_missing_warnings = match_files_by_order(non_train_grouped['pdf'], non_train_grouped['xml'])
        # 特殊处理：如果发现华住酒店文件，尝试智能匹配
        orders = smart_match_hotel_files(orders, extract_dir)
        
        # 如果ZIP类型是unknown但包含华住酒店文件，也尝试酒店匹配
        if zip_type == 'unknown' and any('dzfp_' in Path(pdf).name for pdf in non_train_grouped['pdf']):
            logger.info("🔍 检测到华住酒店发票，尝试酒店文件匹配")
            hotel_orders, hotel_warnings = match_hotel_files_by_hash(non_train_grouped['pdf'], non_train_grouped['xml'], extract_dir)
            if hotel_orders:
                logger.info(f"✅ 成功匹配到 {len(hotel_orders)} 个酒店订单")
                orders.update(hotel_orders)
                xml_missing_warnings.extend(hotel_warnings)
    
    results = []
    
    # 处理每个订单
    order_count = 0
    for order_id, order_data in orders.items():
        # 检查是否有足够的文件进行处理
        itinerary_path = order_data['pdfs']['itinerary']
        invoice_path = order_data['pdfs']['invoice']
        hotel_bill_path = order_data['pdfs'].get('hotel_bill')
        
        if not itinerary_path and not invoice_path:
            logger.warning(f"订单 {order_id} 没有PDF文件，跳过处理")
            continue
        
        # 使用简单的序号作为文件名前缀，避免使用中文文件名
        order_count += 1
        
        # 生成输出文件名 (使用序号和随机字符串，避免使用可能包含中文的order_id)
        output_filename = f"order_{order_count}_{uuid.uuid4().hex[:8]}.pdf"
        output_path = Path(current_app.config['OUTPUT_FOLDER']) / output_filename
        
        logger.info(f"处理订单 {order_id} (序号 {order_count})，输出文件: {output_filename}")
        
        # 智能拼接PDF（根据文件类型决定拼接方式）
        try:
            # 判断是住宿记录还是打车行程单
            if invoice_path and hotel_bill_path:
                # 住宿记录：发票+结账单
                logger.info(f"🏨 检测到住宿记录，处理发票+结账单拼接")
                if create_hotel_combined_pdf(invoice_path, hotel_bill_path, output_path):
                    logger.info(f"住宿拼接成功，输出文件: {output_path}")
                    
                    # 添加处理结果
                    results.append({
                        'order_id': order_id,
                        'amount': order_data['amount'],
                        'output_file': output_filename,
                        'has_itinerary': False,
                        'has_invoice': True,
                        'has_hotel_bill': True,
                        'page_count': 1,
                        'combined_type': 'hotel_accommodation'
                    })
                    logger.info(f"订单 {order_id} 住宿记录处理成功")
                else:
                    logger.error(f"住宿拼接失败，订单 {order_id}")
            elif itinerary_path and invoice_path:
                # 单个行程单：行程单+发票（保持原有逻辑）
                logger.info(f"🚗 检测到单个行程单，处理行程单+发票拼接")
                
                # 获取行程单页数
                page_count = 1  # 默认1页
                try:
                    from PyPDF2 import PdfReader
                    with open(itinerary_path, 'rb') as f:
                        reader = PdfReader(f)
                        page_count = len(reader.pages)
                        logger.info(f"行程单页数: {page_count}")
                except Exception as e:
                    logger.warning(f"无法获取行程单页数，使用默认值1: {e}")
                
                # 在处理拼接之前，先提取原始表格数据并缓存
                raw_table_data = None
                try:
                    logger.info(f"🚗 开始提取原始表格数据: {itinerary_path}")
                    raw_table_data = extract_trip_info_from_itinerary(itinerary_path)
                    if raw_table_data:
                        logger.info(f"✅ 成功提取到原始表格数据，行数: {len(raw_table_data)}")
                    else:
                        logger.warning(f"⚠️ 未能提取到原始表格数据")
                except Exception as e:
                    logger.error(f"❌ 提取原始表格数据失败: {e}")
                
                # 使用智能拼接函数
                if create_smart_combined_pdf(itinerary_path, invoice_path, output_path, page_count):
                    logger.info(f"智能拼接成功，输出文件: {output_path}")
                    
                    # 添加处理结果，包含提取的原始表格数据
                    result = {
                        'order_id': order_id,
                        'amount': order_data['amount'],
                        'output_file': output_filename,
                        'has_itinerary': True,
                        'has_invoice': True,
                        'has_hotel_bill': False,
                        'page_count': page_count,
                        'combined_type': 'single_page' if page_count == 1 else 'multi_page',
                        'raw_table_data': raw_table_data,  # 缓存原始表格数据
                        'itinerary_file': itinerary_path  # 保存原始行程单文件路径
                    }
                    if order_data.get('didi_group_key'):
                        result['didi_group_key'] = order_data.get('didi_group_key')
                    if order_data.get('didi_invoice_number'):
                        result['didi_invoice_number'] = order_data.get('didi_invoice_number')
                    results.append(result)
                    logger.info(f"订单 {order_id} 处理成功，包含原始表格数据行数: {len(raw_table_data) if raw_table_data else 0}")
                else:
                    logger.error(f"智能拼接失败，订单 {order_id}")
            else:
                logger.warning(f"订单 {order_id} 文件组合不完整，跳过处理")
                
        except Exception as e:
            logger.error(f"处理订单 {order_id} 时出错: {str(e)}")
    
    # 处理交通票据（火车票/机票）：严格独立于网约车/酒店逻辑，底层复用同一套排版/拖拽/整合逻辑
    train_ticket_items = _collect_train_ticket_pages(transport_ticket_pdfs)
    train_ticket_count = len(train_ticket_items)
    flight_ticket_count = len([item for item in train_ticket_items if item.get("ticket_type") == "flight"])
    rail_ticket_count = train_ticket_count - flight_ticket_count
    train_group_count = 0
    train_amount = 0.0
    flight_amount = 0.0
    if train_ticket_count > 0:
        train_groups = _split_train_ticket_groups(train_ticket_items)
        train_group_count = len(train_groups)
        logger.info(f"🚆✈️ 交通票据分组完成: total={train_ticket_count}, train={rail_ticket_count}, flight={flight_ticket_count}, groups={train_group_count}")

        for group_index, ticket_group in enumerate(train_groups, start=1):
            output_filename = f"train_{group_index}_{uuid.uuid4().hex[:8]}.pdf"
            output_path = Path(current_app.config['OUTPUT_FOLDER']) / output_filename
            ok = create_train_ticket_layout_pdf(ticket_group, output_path)
            if not ok:
                logger.error(f"❌ 火车票组 {group_index} 排版失败")
                continue

            group_size = len(ticket_group)
            group_amount = round(sum(item.get("amount", 0.0) for item in ticket_group), 2)
            group_train_count = len([item for item in ticket_group if item.get("ticket_type") != "flight"])
            group_flight_count = len([item for item in ticket_group if item.get("ticket_type") == "flight"])
            group_train_amount = round(sum(float(item.get("amount", 0.0) or 0.0) for item in ticket_group if item.get("ticket_type") != "flight"), 2)
            group_flight_amount = round(sum(float(item.get("amount", 0.0) or 0.0) for item in ticket_group if item.get("ticket_type") == "flight"), 2)
            train_amount += group_train_amount
            flight_amount += group_flight_amount
            if group_size == 1:
                combined_type = 'flight_single' if group_flight_count == 1 else 'train_single'
            else:
                combined_type = 'ticket_double'

            # 订单名优先使用 zip/pdf 名；单票可直接显示来源，分组显示组名
            if group_size == 1:
                source = ticket_group[0]
                order_id = Path(source.get("source_name", f"train_{group_index}")).stem
            else:
                order_id = f"train_group_{group_index}"

            # 组内行程展示：优先 from->to，否则用 display_name
            route_parts = []
            for item in ticket_group:
                frm = (item.get("from_station") or "").strip()
                to = (item.get("to_station") or "").strip()
                tno = (item.get("train_no") or "").strip()
                fno = (item.get("flight_no") or "").strip()
                if frm and to and frm.lower() != to.lower():
                    segment = f"{frm}→{to}"
                    if tno:
                        segment = f"{segment}({tno})"
                    elif fno:
                        segment = f"{segment}({fno})"
                    route_parts.append(segment)
                elif item.get("display_name"):
                    route_parts.append(item.get("display_name"))

            results.append({
                'order_id': order_id,
                'amount': group_amount,
                'output_file': output_filename,
                'has_itinerary': False,
                'has_invoice': False,
                'has_hotel_bill': False,
                'has_train_ticket': group_train_count > 0,
                'has_flight_ticket': group_flight_count > 0,
                'has_transport_ticket': True,
                'train_ticket_count': group_size,
                'rail_ticket_count': group_train_count,
                'flight_ticket_count': group_flight_count,
                'train_amount': group_train_amount,
                'flight_amount': group_flight_amount,
                'train_ticket_files': [item.get("source_name") for item in ticket_group],
                'train_ticket_pages': [item.get("page_no") for item in ticket_group],
                'train_routes': route_parts,
                'train_ticket_items': ticket_group,
                'page_count': 1,
                'combined_type': combined_type,
            })
            logger.info(
                f"✅ 火车票组 {group_index} 处理成功: tickets={group_size}, amount={group_amount:.2f}, layout={combined_type}, out={output_filename}"
            )

    logger.info(f"所有订单处理完成，成功处理 {len(results)} 个订单/批次")
    
    # 分类统计金额和警告
    taxi_amount = 0
    hotel_amount = 0
    taxi_warnings = []
    hotel_warnings = []
    
    # 统计各类订单的金额
    for order_id, order_data in orders.items():
        amount = order_data.get('amount', 0)
        if order_id.startswith('hotel_'):
            hotel_amount += amount
        else:
            taxi_amount += amount
    
    # 分类警告信息
    for warning in xml_missing_warnings:
        if warning.get('type') == 'hotel':
            hotel_warnings.append(warning)
        else:
            taxi_warnings.append(warning)
    
    # 记录分类统计结果
    logger.info(f"📊 金额统计结果:")
    logger.info(f"   🚗 网约车总金额: {taxi_amount:.2f}元 ({len([order_id for order_id in orders.keys() if not order_id.startswith('hotel_')])}个订单)")
    logger.info(f"   🏨 酒店总金额: {hotel_amount:.2f}元 ({len([order_id for order_id in orders.keys() if order_id.startswith('hotel_')])}个订单)")
    logger.info(f"   🚆 火车票总金额: {train_amount:.2f}元 ({rail_ticket_count}张)")
    logger.info(f"   ✈️ 机票总金额: {flight_amount:.2f}元 ({flight_ticket_count}张)")
    logger.info(f"   💰 总金额: {taxi_amount + hotel_amount + train_amount + flight_amount:.2f}元")
    
    # 记录分类警告
    if taxi_warnings:
        logger.warning(f"⚠️ 网约车相关问题 ({len(taxi_warnings)}个):")
        for warning in taxi_warnings:
            logger.warning(f"   🚗 订单 {warning['order_id']}: {warning['reason']} -> {warning['impact']}")
    
    if hotel_warnings:
        logger.warning(f"⚠️ 酒店相关问题 ({len(hotel_warnings)}个):")
        for warning in hotel_warnings:
            logger.warning(f"   🏨 订单 {warning['order_id']}: {warning['reason']} -> {warning['impact']}")
    
    # 创建分类统计信息
    classification_info = {
        'taxi_amount': taxi_amount,
        'hotel_amount': hotel_amount,
        'train_amount': round(train_amount, 2),
        'flight_amount': flight_amount,
        'total_amount': round(taxi_amount + hotel_amount + train_amount + flight_amount, 2),
        'taxi_orders': len([order_id for order_id in orders.keys() if not order_id.startswith('hotel_')]),
        'hotel_orders': len([order_id for order_id in orders.keys() if order_id.startswith('hotel_')]),
        'train_tickets': rail_ticket_count,
        'flight_tickets': flight_ticket_count,
        'train_groups': train_group_count,
        'taxi_warnings': taxi_warnings,
        'hotel_warnings': hotel_warnings
    }
    
    return results, taxi_warnings, classification_info


def merge_processed_pdfs(processed_files, output_path):
    """
    拼接多个已处理的PDF文件
    
    Args:
        processed_files: 已处理的文件列表，每个文件包含output_file等信息
        output_path: 输出文件路径
    
    Returns:
        bool: 拼接是否成功
    """
    logger = current_app.logger
    logger.info(f"开始拼接 {len(processed_files)} 个PDF文件")
    
    try:
        # 检查是否有必要的工具
        import subprocess
        import shutil
        if not shutil.which('pdftk'):
            logger.warning("未找到pdftk工具，无法合并PDF")
            return False
        
        # 按类型分类文件：酒店文件优先，然后是网约车文件
        hotel_files = []
        taxi_files = []
        
        for file_info in processed_files:
            output_file = file_info.get('output_file')
            if not output_file:
                continue
                
            # 构建完整文件路径
            from app import Config
            full_path = os.path.join(Config.OUTPUT_FOLDER, output_file)
            
            if not os.path.exists(full_path):
                logger.warning(f"文件不存在，跳过: {full_path}")
                continue
            
            # 根据文件类型分类
            if file_info.get('combined_type') == 'hotel_accommodation':
                hotel_files.append(full_path)
                logger.info(f"🏨 添加酒店文件: {output_file}")
            else:
                taxi_files.append(full_path)
                logger.info(f"🚗 添加网约车文件: {output_file}")
        
        # 合并文件列表：酒店文件在前，网约车文件在后
        all_files = hotel_files + taxi_files
        
        if not all_files:
            logger.warning("没有找到可拼接的文件")
            return False
        
        logger.info(f"📋 拼接顺序: {len(hotel_files)} 个酒店文件 + {len(taxi_files)} 个网约车文件")
        
        # 使用pdftk进行拼接
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_combined = Path(temp_dir) / f"temp_combined_{uuid.uuid4().hex[:8]}.pdf"
        
        try:
            # 构建pdftk命令
            cmd = ['pdftk'] + all_files + ['cat', 'output', temp_combined]
            
            logger.info(f"🔄 执行拼接命令: {' '.join(cmd[:3])}... (共{len(all_files)}个文件)")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            if os.path.exists(temp_combined):
                # 验证拼接结果
                file_size = os.path.getsize(temp_combined)
                logger.info(f"📊 临时拼接文件大小: {file_size} bytes")
                
                if file_size < 1000:
                    logger.error("❌ 拼接文件过小，可能拼接失败")
                    return False
                
                # 移动到最终输出路径
                import shutil
                shutil.move(temp_combined, output_path)
                
                # 验证最终文件
                if os.path.exists(output_path):
                    final_size = os.path.getsize(output_path)
                    logger.info(f"✅ PDF拼接成功!")
                    logger.info(f"   输出文件: {output_path}")
                    logger.info(f"   文件大小: {final_size} bytes")
                    logger.info(f"   拼接文件数: {len(all_files)}")
                    logger.info(f"   拼接顺序: 酒店文件({len(hotel_files)}) + 网约车文件({len(taxi_files)})")
                    return True
                else:
                    logger.error("❌ 最终输出文件未生成")
                    return False
            else:
                logger.error("❌ 临时拼接文件未生成")
                return False
                
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ pdftk拼接失败: {e}")
            logger.error(f"   错误输出: {e.stderr}")
            return False
        finally:
            # 清理临时文件
            if os.path.exists(temp_combined):
                try:
                    os.remove(temp_combined)
                except Exception as e:
                    logger.warning(f"清理临时文件失败: {e}")
        
    except Exception as e:
        logger.error(f"❌ PDF拼接过程出错: {e}")
        return False


def create_download_collection(processed_files, collection_name="报销单据合集"):
    """
    创建下载合集
    
    Args:
        processed_files: 已处理的文件列表
        collection_name: 合集名称
    
    Returns:
        dict: 包含成功状态和文件路径的字典
    """
    logger = current_app.logger
    logger.info(f"开始创建下载合集: {collection_name}")
    
    try:
        # 生成输出文件名
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{collection_name}_{timestamp}.pdf"
        
        from app import Config
        output_path = os.path.join(Config.OUTPUT_FOLDER, output_filename)
        
        # 调用拼接功能
        success = merge_processed_pdfs(processed_files, output_path)
        
        if success:
            logger.info(f"✅ 下载合集创建成功: {output_filename}")
            return {
                'success': True,
                'filename': output_filename,
                'file_path': output_path,
                'file_count': len(processed_files)
            }
        else:
            logger.error("❌ 下载合集创建失败")
            return {
                'success': False,
                'message': 'PDF拼接失败'
            }
            
    except Exception as e:
        logger.error(f"❌ 创建下载合集出错: {e}")
        return {
            'success': False,
            'message': f'创建合集时出错: {str(e)}'
        }


def create_train_merged_entry(processed_files, merged_name_prefix="火车票整合预览"):
    """
    从已处理结果中生成“跨ZIP火车票整合条目”。
    规则：
    - 聚合所有火车票条目（支持增量）
    - 按 1/2/4 张规则重新布局
    - 输出一个可预览/可打印的合并PDF
    """
    logger = current_app.logger
    output_folder = current_app.config['OUTPUT_FOLDER']

    # 收集所有火车票明细项
    merged_items = []
    seen_item_keys = set()

    def _train_item_key(item):
        """
        火车票条目判重键（不要包含临时路径）。
        以票面语义信息为主，避免同一张票在不同上传会话被重复计入。
        """
        source_name = str(item.get('source_name', '') or '').strip().lower()
        page_no = int(item.get('page_no', 1) or 1)
        ticket_type = str(item.get('ticket_type', 'train') or 'train').strip().lower()
        train_no = str(item.get('train_no', '') or '').strip().upper()
        flight_no = str(item.get('flight_no', '') or '').strip().upper()
        from_station = str(item.get('from_station', '') or '').strip().lower()
        to_station = str(item.get('to_station', '') or '').strip().lower()
        amount = f"{float(item.get('amount', 0) or 0):.2f}"

        # 优先用来源名+页码，通常已足够稳定（你的样例就是订单号.pdf）
        if source_name:
            return ("src", ticket_type, source_name, page_no)

        # 来源名缺失时退化到语义指纹
        return ("sig", ticket_type, train_no, flight_no, from_station, to_station, amount, page_no)
    def _sort_index(value, default_index):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default_index

    sorted_processed_files = sorted(
        enumerate(processed_files),
        key=lambda pair: (_sort_index(pair[1].get('train_sort_index'), pair[0]), pair[0])
    )

    for file_order, file_info in sorted_processed_files:
        combined_type = str(file_info.get('combined_type', ''))
        if not (
            file_info.get('has_train_ticket')
            or file_info.get('has_flight_ticket')
            or file_info.get('has_transport_ticket')
            or combined_type.startswith(('train_', 'flight_', 'ticket_'))
        ):
            continue

        items = file_info.get('train_ticket_items') or []
        if items:
            sorted_items = sorted(
                enumerate(items),
                key=lambda pair: (_sort_index(pair[1].get('train_sort_index'), file_order * 1000 + pair[0]), pair[0])
            )
            for _, item in sorted_items:
                key = _train_item_key(item)
                if key in seen_item_keys:
                    continue
                seen_item_keys.add(key)
                merged_items.append(item)
            continue

        # 兜底：旧结果没有 train_ticket_items 时，至少把其输出页作为一个票项参与合并
        output_file = file_info.get('output_file')
        if output_file:
            fallback_item = {
                'pdf_path': os.path.join(output_folder, output_file),
                'page_no': 1,
                'amount': float(file_info.get('amount', 0) or 0),
                'source_name': output_file,
                'ticket_type': 'flight' if file_info.get('has_flight_ticket') else 'train',
                'train_no': '',
                'flight_no': '',
                'from_station': '',
                'to_station': '',
                'display_name': Path(output_file).stem,
            }
            key = _train_item_key(fallback_item)
            if key not in seen_item_keys:
                seen_item_keys.add(key)
                merged_items.append(fallback_item)

    if len(merged_items) <= 1:
        return {
            'success': False,
            'message': '火车票条目不足，至少需要2张才能生成整合条目'
        }

    merge_order = []
    for item in merged_items:
        merge_order.append({
            'source_name': item.get('source_name', ''),
            'display_name': item.get('display_name', ''),
            'ticket_type': item.get('ticket_type', 'train'),
            'amount': float(item.get('amount', 0) or 0),
            'train_sort_index': _sort_index(item.get('train_sort_index'), len(merge_order)),
        })
    logger.info(f"交通票据整合顺序: {merge_order}")

    groups = _split_train_ticket_groups(merged_items)
    import tempfile
    from datetime import datetime

    tmp_files = []
    merged_filename = f"train_merged_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.pdf"
    merged_path = os.path.join(output_folder, merged_filename)

    try:
        # 每个group生成一页，再合并成多页PDF
        for idx, group in enumerate(groups, start=1):
            tmp_path = os.path.join(tempfile.gettempdir(), f"train_group_{idx}_{uuid.uuid4().hex[:8]}.pdf")
            ok = create_train_ticket_layout_pdf(group, tmp_path)
            if not ok:
                logger.error(f"火车票整合预览：第{idx}组布局失败")
                return {'success': False, 'message': f'第{idx}组布局失败'}
            tmp_files.append(tmp_path)

        writer = PdfWriter()
        for tp in tmp_files:
            reader = PdfReader(tp)
            for page in reader.pages:
                writer.add_page(page)
        with open(merged_path, 'wb') as f:
            writer.write(f)

        if (not os.path.exists(merged_path)) or os.path.getsize(merged_path) < 1000:
            return {'success': False, 'message': '整合文件生成失败或为空'}

        total_amount = round(sum(float(i.get('amount', 0) or 0) for i in merged_items), 2)
        rail_items = [i for i in merged_items if i.get("ticket_type") != "flight"]
        flight_items = [i for i in merged_items if i.get("ticket_type") == "flight"]
        rail_amount = round(sum(float(i.get('amount', 0) or 0) for i in rail_items), 2)
        flight_amount = round(sum(float(i.get('amount', 0) or 0) for i in flight_items), 2)
        route_parts = []
        for item in merged_items:
            frm = (item.get("from_station") or "").strip()
            to = (item.get("to_station") or "").strip()
            tno = (item.get("train_no") or "").strip()
            fno = (item.get("flight_no") or "").strip()
            if frm and to and frm.lower() != to.lower():
                seg = f"{frm}→{to}"
                if tno:
                    seg = f"{seg}({tno})"
                elif fno:
                    seg = f"{seg}({fno})"
                route_parts.append(seg)
            elif item.get("display_name"):
                route_parts.append(item.get("display_name"))

        merged_result = {
            'order_id': 'train_merged_all',
            'amount': total_amount,
            'output_file': merged_filename,
            'has_itinerary': False,
            'has_invoice': False,
            'has_hotel_bill': False,
            'has_train_ticket': len(rail_items) > 0,
            'has_flight_ticket': len(flight_items) > 0,
            'has_transport_ticket': True,
            'is_train_merged_entry': True,
            'train_ticket_count': len(merged_items),
            'rail_ticket_count': len(rail_items),
            'flight_ticket_count': len(flight_items),
            'train_amount': rail_amount,
            'flight_amount': flight_amount,
            'train_group_count': len(groups),
            'train_routes': route_parts[:30],
            'train_merge_order': merge_order,
            'page_count': len(groups),
            'combined_type': 'ticket_merged_all',
        }

        return {
            'success': True,
            'message': '火车票整合条目生成成功',
            'result': merged_result,
            'file_path': merged_path,
        }
    except Exception as e:
        logger.error(f"生成火车票整合条目失败: {e}", exc_info=True)
        return {'success': False, 'message': f'生成失败: {str(e)}'}
    finally:
        for tp in tmp_files:
            try:
                if os.path.exists(tp):
                    os.remove(tp)
            except Exception:
                pass


def extract_trip_info_from_itinerary(pdf_path):
    """
    从行程单PDF中提取行程信息（使用pdfplumber + 暂存原始数据）
    
    Args:
        pdf_path: 行程单PDF文件路径
    
    Returns:
        list: 原始表格数据列表，用于后续AI处理
    """
    logger = current_app.logger
    logger.info(f"开始从行程单提取原始表格数据: {pdf_path}")
    
    try:
        import pdfplumber
        
        # 使用pdfplumber lines策略提取表格
        logger.info("使用pdfplumber lines策略提取PDF表格")
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[0]  # 获取第一页
            tables = page.extract_tables(table_settings={
                "vertical_strategy": "lines", 
                "horizontal_strategy": "lines"
            })
            
            if not tables:
                logger.warning("未找到表格数据")
                return []
            
            logger.info(f"找到 {len(tables)} 个表格")
            
            # 返回原始表格数据，不进行解析
            table_data = tables[0]
            logger.info(f"提取到原始表格数据，行数: {len(table_data)}")
            logger.info(f"原始表格数据内容: {table_data}")
            
            # 暂存原始数据，返回给调用方
            return table_data
        
    except Exception as e:
        logger.error(f"从行程单提取原始数据失败: {e}")
        return []


def parse_trip_row_data_with_context(df, row_index, row_data):
    """
    解析DataFrame中一行的行程数据，并尝试从相邻行获取起点信息
    
    Args:
        df: DataFrame对象
        row_index: 当前行索引
        row_data: 当前行数据
    
    Returns:
        dict: 行程信息字典
    """
    import re
    logger = current_app.logger
    
    # 先解析当前行的数据
    trip = parse_trip_row_data(row_data)
    if not trip:
        return None
    
    # 如果起点是"未知起点"，尝试从相邻行获取起点信息
    if trip.get('start_point') == '未知起点':
        logger.info("尝试从相邻行获取起点信息...")
        
        # 收集所有可能的起点信息
        start_point_parts = []
        
        # 检查前一行（可能包含起点的第一部分）
        if row_index - 1 >= 0:
            prev_row = list(df.iloc[row_index - 1])
            prev_row_clean = [str(cell).strip() for cell in prev_row if str(cell).strip() and str(cell).strip() != 'nan']
            
            # 如果前一行有数据且不包含序号，可能是起点信息
            if prev_row_clean and not any(re.match(r'^\d+', str(cell)) for cell in prev_row_clean):
                for cell in prev_row_clean:
                    if cell and not any(keyword in cell for keyword in ['说明：', '页码：', '序号', '服务商', '车型', '上车时间', '城市', '起点', '终点', '金额']):
                        start_point_parts.append(cell)
        
        # 检查下一行（可能包含起点的第二部分）
        if row_index + 1 < len(df):
            next_row = list(df.iloc[row_index + 1])
            next_row_clean = [str(cell).strip() for cell in next_row if str(cell).strip() and str(cell).strip() != 'nan']
            
            # 如果下一行有数据且不包含序号，可能是起点信息
            if next_row_clean and not any(re.match(r'^\d+', str(cell)) for cell in next_row_clean):
                for cell in next_row_clean:
                    if cell and not any(keyword in cell for keyword in ['说明：', '页码：', '序号', '服务商', '车型', '上车时间', '城市', '起点', '终点', '金额']):
                        start_point_parts.append(cell)
        
        # 组合起点信息
        if start_point_parts:
            trip['start_point'] = ' '.join(start_point_parts)
            logger.info(f"组合起点信息: {trip['start_point']}")
    
    return trip


def parse_trip_row_data(row_data):
    """
    解析DataFrame中一行的行程数据
    
    Args:
        row_data: 行数据列表
    
    Returns:
        dict: 行程信息字典
    """
    logger = current_app.logger
    
    # 过滤掉空值和nan
    clean_cells = []
    for cell in row_data:
        cell_str = str(cell).strip()
        if cell_str and cell_str != 'nan':
            clean_cells.append(cell_str)
    
    if len(clean_cells) < 3:
        logger.warning(f"行数据不足: {clean_cells}")
        return None
    
    # 根据raw_data重新分析数据结构：
    # 第0个数据：序号\n服务商 (如 "2\n旅程易到")
    # 第1个数据：车型 时间 (如 "旅程易到经济型 2024-06-20 18:59")
    # 第2个数据：城市\n起点 (如 "北京市\n航天智能院")
    # 第3个数据：终点 (如 "汉庭优佳北京石景山首钢园酒店")
    # 第4个数据：金额 (如 "16.12元")
    
    trip = {}
    
    # 解析第0个数据：序号和服务商
    if len(clean_cells) > 0:
        first_cell = clean_cells[0]
        if '\n' in first_cell:
            parts = first_cell.split('\n')
            trip['sequence'] = parts[0].strip()
            trip['service_provider'] = parts[1].strip() if len(parts) > 1 else '未知'
        else:
            trip['sequence'] = first_cell
            trip['service_provider'] = '未知'
    
    # 解析第1个数据：车型和时间
    if len(clean_cells) > 1:
        second_cell = clean_cells[1]
        # 找到第一个空格的位置，前面是车型，后面是时间
        space_index = second_cell.find(' ')
        if space_index > 0:
            trip['car_type'] = second_cell[:space_index].strip()
            trip['pickup_time'] = second_cell[space_index+1:].strip()
        else:
            trip['car_type'] = second_cell
            trip['pickup_time'] = '未知时间'
    
    # 解析第2个数据：城市和起点
    if len(clean_cells) > 2:
        third_cell = clean_cells[2]
        if '\n' in third_cell:
            parts = third_cell.split('\n')
            trip['city'] = parts[0].strip()
            trip['start_point'] = parts[1].strip() if len(parts) > 1 else '未知起点'
        else:
            trip['city'] = third_cell
            trip['start_point'] = '未知起点'
    
    # 解析第3个数据：终点
    if len(clean_cells) > 3:
        trip['end_point'] = clean_cells[3]
    
    # 解析第4个数据：金额
    if len(clean_cells) > 4:
        trip['amount'] = clean_cells[4]
    
    # 设置默认值
    trip.setdefault('sequence', '未知')
    trip.setdefault('service_provider', '未知')
    trip.setdefault('car_type', '未知')
    trip.setdefault('pickup_time', '未知时间')
    trip.setdefault('city', '未知城市')
    trip.setdefault('start_point', '未知起点')
    trip.setdefault('end_point', '未知终点')
    trip.setdefault('amount', '0元')
    trip['raw_data'] = clean_cells
    
    return trip


def parse_trip_info_simple(text):
    """
    简化的行程信息解析
    按照用户建议：识别序号行，识别说明行，提取中间内容，去掉空行
    
    Args:
        text: PDF提取的文本内容
    
    Returns:
        list: 行程信息列表
    """
    logger = current_app.logger
    logger.info("使用简化解析方法")
    
    try:
        lines = text.split('\n')
        logger.info(f"文本总行数: {len(lines)}")
        
        trips = []
        current_trip = []
        in_trip = False
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:  # 跳过空行
                continue
            
            logger.debug(f"第{i+1}行: '{line}'")
            
            # 识别序号行（纯数字）
            if line.isdigit():
                # 如果之前有行程数据，保存它
                if current_trip and in_trip:
                    trip_info = parse_single_trip(current_trip)
                    if trip_info:
                        trips.append(trip_info)
                        logger.info(f"解析到行程: {trip_info}")
                
                # 开始新的行程
                current_trip = [line]  # 序号
                in_trip = True
                logger.debug(f"发现序号行: {line}")
                continue
            
            # 如果在行程中，收集数据
            if in_trip:
                current_trip.append(line)
                
                # 识别说明行（包含"旅程"、"经济型"等关键词）
                if any(keyword in line for keyword in ['旅程', '经济型', '出行', '打车']):
                    logger.debug(f"发现说明行: {line}")
                    # 说明行通常是行程的结束标志
                    trip_info = parse_single_trip(current_trip)
                    if trip_info:
                        trips.append(trip_info)
                        logger.info(f"解析到行程: {trip_info}")
                    current_trip = []
                    in_trip = False
        
        # 处理最后一个行程
        if current_trip and in_trip:
            trip_info = parse_single_trip(current_trip)
            if trip_info:
                trips.append(trip_info)
                logger.info(f"解析到最后一个行程: {trip_info}")
        
        logger.info(f"总共解析到 {len(trips)} 个行程")
        return trips
        
    except Exception as e:
        logger.error(f"简化解析失败: {e}")
        return []


def parse_single_trip(trip_lines):
    """
    解析单个行程的数据
    
    Args:
        trip_lines: 行程相关的文本行列表
    
    Returns:
        dict: 行程信息字典
    """
    logger = current_app.logger
    
    try:
        if len(trip_lines) < 3:
            logger.warning(f"行程数据不足: {trip_lines}")
            return None
        
        # 去掉空行
        clean_lines = [line.strip() for line in trip_lines if line.strip()]
        
        if len(clean_lines) < 3:
            logger.warning(f"清理后行程数据不足: {clean_lines}")
            return None
        
        # 基本结构：序号, 说明行, 时间, 城市, 起点, 终点, 金额
        trip = {
            'sequence': clean_lines[0] if len(clean_lines) > 0 else '未知',
            'description': clean_lines[1] if len(clean_lines) > 1 else '未知',
            'pickup_time': clean_lines[2] if len(clean_lines) > 2 else '未知时间',
            'city': clean_lines[3] if len(clean_lines) > 3 else '未知城市',
            'start_point': clean_lines[4] if len(clean_lines) > 4 else '未知起点',
            'end_point': clean_lines[5] if len(clean_lines) > 5 else '未知终点',
            'amount': clean_lines[6] if len(clean_lines) > 6 else '0元',
            'raw_data': clean_lines  # 保存原始数据
        }
        
        logger.debug(f"解析单个行程: {trip}")
        return trip
        
    except Exception as e:
        logger.error(f"解析单个行程失败: {e}")
        return None


def parse_table_to_trips(df):
    """
    将camelot提取的表格数据转换为行程信息
    处理camelot stream模式提取的表格格式
    
    Args:
        df: pandas DataFrame
    
    Returns:
        list: 行程信息列表
    """
    logger = current_app.logger
    trips = []
    
    try:
        logger.info(f"开始解析表格数据，形状: {df.shape}")
        
        # 第一步：识别打车平台
        platform = identify_ride_platform(df)
        logger.info(f"识别到打车平台: {platform}")
        
        # 第二步：根据平台使用对应的解析逻辑
        if platform == "高德地图":
            trips = parse_amap_trips(df)
        else:
            logger.warning(f"未知的打车平台: {platform}")
            return []
        
        return trips
        
    except Exception as e:
        logger.error(f"解析表格数据失败: {e}")
        return []


def identify_ride_platform(df):
    """
    识别打车平台
    """
    logger = current_app.logger
    
    try:
        # 检查表格中是否包含平台标识
        for i, row in df.iterrows():
            for col in df.columns:
                cell_data = str(row[col]).strip()
                if '高德地图' in cell_data or 'AMAP' in cell_data:
                    return "高德地图"
                elif '滴滴' in cell_data or 'DIDI' in cell_data:
                    return "滴滴出行"
                elif '美团' in cell_data or 'MEITUAN' in cell_data:
                    return "美团打车"
                elif '曹操' in cell_data or 'CAOCAO' in cell_data:
                    return "曹操出行"
        
        # 如果没有明确标识，根据服务商推断
        for i, row in df.iterrows():
            for col in df.columns:
                cell_data = str(row[col]).strip()
                if '旅程易到' in cell_data:
                    return "高德地图"  # 旅程易到是高德地图的服务商
        
        return "未知平台"
        
    except Exception as e:
        logger.error(f"识别打车平台失败: {e}")
        return "未知平台"


def parse_amap_trips(df):
    """
    解析高德地图的行程数据
    根据实际数据结构，行程数据在行6, 8, 10
    """
    logger = current_app.logger
    trips = []
    
    try:
        logger.info("开始解析高德地图行程数据")
        
        # 从stream提取的数据中，行程数据在行6, 8, 10
        trip_rows = [6, 8, 10]
        
        for row_idx in trip_rows:
            if row_idx < len(df):
                row = df.iloc[row_idx]
                row_data = []
                for col in df.columns:
                    cell_data = str(row[col]).strip()
                    if cell_data and cell_data != 'nan':
                        row_data.append(cell_data)
                
                if row_data:
                    logger.info(f"处理高德地图行程行 {row_idx}: {row_data}")
                    trip = parse_amap_trip_row(row_data)
                    if trip:
                        trips.append(trip)
                        logger.info(f"解析到高德地图行程: {trip}")
        
        return trips
        
    except Exception as e:
        logger.error(f"解析高德地图行程数据失败: {e}")
        return []


def parse_trip_from_lines(lines):
    """
    从分割后的行中解析行程信息
    """
    logger = current_app.logger
    
    try:
        # 查找序号
        sequence = None
        for line in lines:
            if line.strip().isdigit():
                sequence = line.strip()
                break
        
        if not sequence:
            return None
        
        # 查找金额
        amount = 0.0
        for line in lines:
            amount_match = re.search(r'(\d+\.?\d*)\s*元', line)
            if amount_match:
                amount = float(amount_match.group(1))
                break
        
        # 查找时间
        pickup_time = None
        for line in lines:
            time_match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})', line)
            if time_match:
                pickup_time = time_match.group(1)
                break
        
        # 查找城市
        city = None
        for line in lines:
            if '北京市' in line or '上海市' in line or '广州市' in line or '深圳市' in line:
                city = line.strip()
                break
        
        # 查找起点和终点（简化处理）
        start_point = None
        end_point = None
        
        # 根据实际数据结构调整
        if len(lines) >= 6:
            # 假设起点在前，终点在后
            for i, line in enumerate(lines):
                if '北京南站' in line or '航天智能院' in line or '汉庭' in line:
                    if not start_point:
                        start_point = line.strip()
                    elif not end_point:
                        end_point = line.strip()
        
        trip = {
            'sequence': sequence,
            'service_provider': '旅程易到',  # 从数据中可以看出
            'car_type': '旅程易到经济型',  # 从数据中可以看出
            'pickup_time': pickup_time or '未知时间',
            'city': city or '未知城市',
            'start_point': start_point or '未知起点',
            'end_point': end_point or '未知终点',
            'amount': amount
        }
        
        return trip
        
    except Exception as e:
        logger.error(f"解析行程信息失败: {e}")
        return None


def parse_trip_from_stream_row(row_data):
    """
    从stream模式提取的行数据中解析行程信息
    根据测试结果，数据格式为：
    行6: ['1\n旅程易到', '旅程易到经济型 2024-06-19 12:32', '北京市', '航天智能院', '53.89元']
    行8: ['2\n旅程易到', '旅程易到经济型 2024-06-20 18:59', '北京市', '汉庭优佳北京石景山首钢园酒店', '16.12元']
    行10: ['3\n旅程易到', '旅程易到经济型 2024-06-21 08:18', '北京市', '北京南站(东进站口)', '74.55元']
    """
    logger = current_app.logger
    
    try:
        if len(row_data) < 5:
            logger.warning(f"行数据不足: {row_data}")
            return None
        
        # 解析第一列：序号和服务商
        first_col = row_data[0]
        if '\n' in first_col:
            parts = first_col.split('\n')
            sequence = parts[0].strip()
            service_provider = parts[1].strip() if len(parts) > 1 else '旅程易到'
        else:
            sequence = first_col.strip()
            service_provider = '旅程易到'
        
        # 解析第二列：车型和上车时间
        second_col = row_data[1]
        if '旅程易到经济型' in second_col:
            car_type = '旅程易到经济型'
            # 提取时间
            time_match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})', second_col)
            pickup_time = time_match.group(1) if time_match else '未知时间'
        else:
            car_type = '旅程易到经济型'
            pickup_time = '未知时间'
        
        # 解析第三列：城市
        city = row_data[2].strip() if len(row_data) > 2 else '未知城市'
        
        # 解析第四列：起点或终点
        location = row_data[3].strip() if len(row_data) > 3 else '未知地点'
        
        # 解析第五列：金额
        amount = 0.0
        if len(row_data) > 4:
            amount_str = row_data[4]
            amount_match = re.search(r'(\d+\.?\d*)\s*元', amount_str)
            if amount_match:
                amount = float(amount_match.group(1))
        
        # 根据实际数据结构，需要智能判断起点和终点
        # 从测试数据可以看到：
        # 行程1: 起点=北京南站-东停车场M, 终点=航天智能院
        # 行程2: 起点=航天智能院, 终点=汉庭优佳北京石景山首钢园酒店  
        # 行程3: 起点=汉庭优佳酒店, 终点=北京南站(东进站口)
        
        start_point = location
        end_point = location  # 暂时设为相同，需要根据上下文调整
        
        trip = {
            'sequence': sequence,
            'service_provider': service_provider,
            'car_type': car_type,
            'pickup_time': pickup_time,
            'city': city,
            'start_point': start_point,
            'end_point': end_point,
            'amount': amount
        }
        
        return trip
        
    except Exception as e:
        logger.error(f"解析stream行数据失败: {e}")
        return None


def parse_amap_trip_row(row_data):
    """
    解析高德地图单行行程数据
    简化版本：直接使用camelot提取的原始数据
    """
    logger = current_app.logger
    
    try:
        if len(row_data) < 5:
            logger.warning(f"高德地图行数据不足: {row_data}")
            return None
        
        # 直接使用原始数据，不做复杂解析
        trip = {
            'raw_data': row_data,  # 保存原始数据
            'sequence': row_data[0].strip() if len(row_data) > 0 else '未知',
            'pickup_time': row_data[1].strip() if len(row_data) > 1 else '未知时间',
            'city': row_data[2].strip() if len(row_data) > 2 else '未知城市',
            'location': row_data[3].strip() if len(row_data) > 3 else '未知地点',
            'amount': row_data[4].strip() if len(row_data) > 4 else '0元'
        }
        
        return trip
        
    except Exception as e:
        logger.error(f"解析高德地图行程行数据失败: {e}")
        return None


def parse_trip_info_simple_text(text):
    """
    简单的文本解析方法（回退用）
    """
    logger = current_app.logger
    trips = []
    
    try:
        lines = text.split('\n')
        
        # 查找数据开始位置
        data_start = -1
        for i, line in enumerate(lines):
            if line.strip() == '1':
                data_start = i
                break
        
        if data_start == -1:
            logger.warning("未找到数据开始位置")
            return []
        
        # 简单解析：查找包含金额的行
        amount_pattern = r'(\d+\.?\d*)\s*元'
        for i, line in enumerate(lines[data_start:], data_start):
            line = line.strip()
            amount_match = re.search(amount_pattern, line)
            if amount_match:
                amount = float(amount_match.group(1))
                
                # 简单提取其他信息
                trip = {
                    'sequence': str(len(trips) + 1),
                    'pickup_time': '未知时间',
                    'city': '未知城市',
                    'start_point': '未知起点',
                    'end_point': '未知终点',
                    'amount': amount
                }
                trips.append(trip)
                logger.info(f"简单解析到行程: {trip}")
        
        return trips
        
    except Exception as e:
        logger.error(f"简单文本解析失败: {e}")
        return []


# 废弃的文本解析方法 - 使用camelot-py替代
# def parse_trip_info_from_text(text):
#     """
#     从文本中解析行程信息（基于实际PDF格式）
#     
#     Args:
#         text: PDF提取的文本内容
#     
#     Returns:
#         list: 行程信息列表
#     """
#     logger = current_app.logger
#     trips = []
#     
#     try:
#         lines = text.split('\n')
#         
#         # 查找数据开始位置（跳过表头）
#         data_start = -1
#         for i, line in enumerate(lines):
#             if line.strip() == '1':  # 第一个序号
#                 data_start = i
#                 break
#         
#         if data_start == -1:
#             logger.warning("未找到数据开始位置")
#             return []
#         
#         logger.info(f"找到数据开始位置: 第{data_start+1}行")
#         
#         # 解析行程数据
#         i = data_start
#         while i < len(lines):
#             line = lines[i].strip()
#             if not line:
#                 i += 1
#                 continue
#             
#             # 跳过说明文字
#             if '说明：' in line or '页码：' in line:
#                 break
#             
#             # 检查是否是序号（新行程开始）
#             if line.isdigit():
#                 trip = {}
#                 trip['sequence'] = line
#                 
#                 # 读取服务商
#                 i += 1
#                 if i < len(lines):
#                     trip['service_provider'] = lines[i].strip()
#                 
#                 # 读取车型
#                 i += 1
#                 if i < len(lines):
#                     trip['car_type'] = lines[i].strip()
#                 
#                 # 读取上车时间
#                 i += 1
#                 if i < len(lines):
#                     trip['pickup_time'] = lines[i].strip()
#                 
#                 # 读取城市
#                 i += 1
#                 if i < len(lines):
#                     trip['city'] = lines[i].strip()
#                 
#                 # 读取起点（可能跨多行）
#                 i += 1
#                 if i < len(lines):
#                     start_point = lines[i].strip()
#                     i += 1
#                     # 检查下一行是否是起点的延续
#                     if i < len(lines) and not lines[i].strip().isdigit() and '元' not in lines[i] and '说明：' not in lines[i]:
#                         start_point += lines[i].strip()
#                         i += 1
#                     trip['start_point'] = start_point
#                 
#                 # 读取终点（可能跨多行）
#                 if i < len(lines):
#                     end_point = lines[i].strip()
#                     i += 1
#                     # 检查下一行是否是终点的延续
#                     if i < len(lines) and not lines[i].strip().isdigit() and '元' not in lines[i] and '说明：' not in lines[i]:
#                         end_point += lines[i].strip()
#                         i += 1
#                     trip['end_point'] = end_point
#                 
#                 # 读取金额
#                 if i < len(lines):
#                     amount_line = lines[i].strip()
#                     amount_match = re.search(r'(\d+\.?\d*)\s*元', amount_line)
#                     if amount_match:
#                         trip['amount'] = float(amount_match.group(1))
#                     i += 1
#                 
#                 trips.append(trip)
#                 logger.info(f"解析到行程: {trip}")
#             else:
#                 i += 1
#         
#         return trips
#         
#     except Exception as e:
#         logger.error(f"解析行程信息失败: {e}")
#         return []


def parse_trip_info_from_text(text):
    """
    从文本中解析行程信息（使用camelot-py库）
    
    Args:
        text: PDF提取的文本内容（暂时不使用，直接使用camelot从PDF提取）
    
    Returns:
        list: 行程信息列表
    """
    logger = current_app.logger
    logger.info("使用camelot-py库解析行程信息")
    
    # 这个方法现在被camelot替代，保留接口兼容性
    return []


def parse_simple_trip_info(lines):
    """
    简单的行程信息解析（备用方案）
    
    Args:
        lines: 文本行列表
    
    Returns:
        list: 行程信息列表
    """
    logger = current_app.logger
    trips = []
    
    try:
        # 查找包含数字和金额的行
        amount_pattern = r'(\d+\.?\d*)\s*元'
        time_pattern = r'(\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{2})'
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # 查找金额
            amount_match = re.search(amount_pattern, line)
            if amount_match:
                amount = float(amount_match.group(1))
                
                # 查找时间
                time_match = re.search(time_pattern, line)
                pickup_time = time_match.group(1) if time_match else "未知时间"
                
                # 尝试提取其他信息
                parts = line.split()
                if len(parts) >= 3:
                    trip = {
                        'sequence': str(len(trips) + 1),  # 序号
                        'pickup_time': pickup_time,  # 上车时间
                        'city': parts[0] if len(parts) > 0 else "未知城市",  # 城市
                        'start_point': parts[1] if len(parts) > 1 else "未知起点",  # 起点
                        'end_point': parts[2] if len(parts) > 2 else "未知终点",  # 终点
                        'amount': amount  # 金额
                    }
                    trips.append(trip)
                    logger.info(f"简单解析到行程: {trip}")
        
        return trips
        
    except Exception as e:
        logger.error(f"简单解析行程信息失败: {e}")
        return []


def generate_trip_records(processed_files):
    """
    生成行程记录字符串
    使用高德打车PDF解析器提取行程信息，支持多文件合并和按时间排序
    
    Args:
        processed_files: 已处理的文件列表
    
    Returns:
        str: 格式化的行程记录字符串
    """
    logger = current_app.logger
    logger.info(f"开始生成行程记录，文件数量: {len(processed_files)}")
    
    try:
        # 检查是否已经有缓存的行程记录
        cached_trip_records = None
        itinerary_files = [f for f in processed_files if f.get('has_itinerary', False)]
        
        logger.info(f"找到 {len(itinerary_files)} 个包含行程单的文件")
        
        # 检查所有行程单文件是否都有缓存
        for file_info in itinerary_files:
            logger.info(f"检查文件 {file_info.get('output_file', '未知')} 的缓存状态")
            if file_info.get('cached_trip_records'):
                cached_trip_records = file_info.get('cached_trip_records')
                logger.info(f"文件 {file_info.get('output_file', '未知')} 有缓存")
            else:
                logger.info(f"文件 {file_info.get('output_file', '未知')} 没有缓存")
                cached_trip_records = None
                break
        
        if cached_trip_records:
            logger.info("所有行程单文件都有缓存，直接返回缓存的行程记录")
            logger.info(f"缓存的行程记录内容: {cached_trip_records}")
            return cached_trip_records
        else:
            logger.info("没有找到完整的缓存，需要重新生成行程记录")
        
        # 如果没有缓存，则生成新的行程记录
        # 导入高德打车PDF解析器
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(project_root))
        from utils.trip_table_parse_enhanced import parse_gaode_itinerary_enhanced
        
        all_trips = []  # 收集所有文件的行程记录
        
        # 遍历所有文件，使用新的解析器提取行程信息
        for file_info in processed_files:
            # 只处理包含行程单的文件
            if not file_info.get('has_itinerary', False):
                continue
            
            # 检查是否有原始行程单文件路径
            itinerary_file = file_info.get('itinerary_file')
            if not itinerary_file or not os.path.exists(itinerary_file):
                logger.warning(f"文件 {file_info.get('output_file', '未知')} 没有找到原始行程单文件路径")
                continue
            
            logger.info(f"开始解析行程单文件: {itinerary_file}")
            try:
                # 使用新的解析器解析高德打车行程单
                parse_result = parse_gaode_itinerary_enhanced(itinerary_file)
                
                if parse_result.get('success') and parse_result.get('trips'):
                    trips = parse_result['trips']
                    logger.info(f"✅ 成功解析文件 {itinerary_file}，获得 {len(trips)} 条行程记录")
                    all_trips.extend(trips)
                else:
                    error_msg = parse_result.get('error', '未知错误')
                    logger.warning(f"⚠️ 解析文件 {itinerary_file} 失败: {error_msg}")
            except Exception as e:
                logger.error(f"❌ 解析文件 {itinerary_file} 时出错: {e}")
                import traceback
                traceback.print_exc()
        
        if not all_trips:
            logger.info("没有找到任何行程记录")
            return "暂无行程记录"
        
        logger.info(f"共收集到 {len(all_trips)} 条行程记录，开始排序和重新编号...")
        
        # 按上车时间排序（解析时间字符串并排序）
        def parse_time_for_sort(trip):
            """解析上车时间用于排序"""
            pickup_time = trip.get('上车时间', '')
            if not pickup_time:
                return (0, 0, 0, 0, 0)  # 默认最早时间
            
            try:
                # 格式: "2024-06-19 12:32"
                import re
                match = re.match(r'(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2})', pickup_time)
                if match:
                    year, month, day, hour, minute = map(int, match.groups())
                    return (year, month, day, hour, minute)
            except:
                pass
            
            return (0, 0, 0, 0, 0)  # 解析失败时返回默认值
        
        # 按时间排序
        all_trips.sort(key=parse_time_for_sort)
        logger.info(f"✅ 行程记录已按时间排序")
        
        # 重新编号
        for index, trip in enumerate(all_trips, start=1):
            trip['序号'] = str(index)
        
        logger.info(f"✅ 行程记录已重新编号，共 {len(all_trips)} 条")
        
        # 将高德解析器的数据格式转换为HTML表格所需的格式
        structured_trips = []
        for trip in all_trips:
            structured_trips.append({
                'sequence': trip.get('序号', ''),
                'service_provider': trip.get('服务商', '未知'),
                'car_type': trip.get('车型', '未知'),
                'pickup_time': trip.get('上车时间', '未知时间'),
                'city': trip.get('城市', '未知城市'),
                'start_point': trip.get('起点', '未知起点'),
                'end_point': trip.get('终点', '未知终点'),
                'amount': f"{trip.get('金额(元)', '0')}元"
            })
        
        logger.info(f"✅ 数据格式转换完成，共 {len(structured_trips)} 条行程记录")
        
        # 生成HTML表格格式的行程记录
        html_table = []
        html_table.append('<div class="trip-records-container">')
        html_table.append('<h4 class="mb-3">📋 行程记录</h4>')
        html_table.append('<div class="table-responsive">')
        html_table.append('<table class="table table-striped table-hover">')
        
        # 表头
        html_table.append('<thead class="table-dark">')
        html_table.append('<tr>')
        html_table.append('<th scope="col">序号</th>')
        html_table.append('<th scope="col">服务商</th>')
        html_table.append('<th scope="col">车型</th>')
        html_table.append('<th scope="col">上车时间</th>')
        html_table.append('<th scope="col">城市</th>')
        html_table.append('<th scope="col">起点</th>')
        html_table.append('<th scope="col">终点</th>')
        html_table.append('<th scope="col">金额</th>')
        html_table.append('</tr>')
        html_table.append('</thead>')
        
        # 表格内容
        html_table.append('<tbody>')
        for trip in structured_trips:
            html_table.append('<tr>')
            html_table.append(f'<td><span class="badge bg-primary">{trip.get("sequence", "未知")}</span></td>')
            html_table.append(f'<td>{trip.get("service_provider", "未知")}</td>')
            html_table.append(f'<td><small class="text-muted">{trip.get("car_type", "未知")}</small></td>')
            html_table.append(f'<td><strong>{trip.get("pickup_time", "未知时间")}</strong></td>')
            html_table.append(f'<td><span class="badge bg-info">{trip.get("city", "未知城市")}</span></td>')
            html_table.append(f'<td>{trip.get("start_point", "未知起点")}</td>')
            html_table.append(f'<td>{trip.get("end_point", "未知终点")}</td>')
            html_table.append(f'<td><span class="badge bg-success">{trip.get("amount", "0元")}</span></td>')
            html_table.append('</tr>')
            logger.info(f"生成行程记录行: {trip.get('sequence')} - {trip.get('pickup_time')} - {trip.get('start_point')} -> {trip.get('end_point')} - {trip.get('amount')}")
        
        html_table.append('</tbody>')
        html_table.append('</table>')
        html_table.append('</div>')
        
        # 统计信息
        total_amount = 0
        for trip in structured_trips:
            amount_str = trip.get('amount', '0元')
            try:
                # 提取金额数字
                import re
                amount_match = re.search(r'(\d+\.?\d*)', amount_str)
                if amount_match:
                    total_amount += float(amount_match.group(1))
            except:
                pass
        
        html_table.append('<div class="mt-3 p-3 bg-light rounded">')
        html_table.append(f'<h6 class="mb-2">📊 统计信息</h6>')
        html_table.append(f'<p class="mb-1"><strong>总行程数：</strong>{len(structured_trips)} 个</p>')
        html_table.append(f'<p class="mb-0"><strong>总金额：</strong><span class="text-success fw-bold">¥{total_amount:.2f}</span></p>')
        html_table.append('</div>')
        html_table.append('</div>')
        
        result = "\n".join(html_table)
        logger.info(f"生成HTML表格格式行程记录完成，共 {len(structured_trips)} 个行程，总金额 ¥{total_amount:.2f}")
        logger.info(f"最终生成的HTML内容长度: {len(result)} 字符")
        
        # 缓存生成的行程记录到所有相关文件中
        for file_info in processed_files:
            if file_info.get('has_itinerary', False):
                file_info['cached_trip_records'] = result
                logger.info(f"已缓存行程记录到文件: {file_info.get('output_file', '未知')}")
                logger.info(f"缓存的内容长度: {len(result)} 字符")
        
        return result
        
    except Exception as e:
        logger.error(f"生成行程记录失败: {e}")
        return f"生成行程记录时出错: {str(e)}" 