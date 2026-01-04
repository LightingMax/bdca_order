#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高德打车PDF行程单解析器

功能：
- 解析高德打车PDF行程单，提取行程信息并返回JSON格式数据
- 使用pymupdf的XY坐标布局分析，智能处理PDF中的换行和表格结构
- 支持提取：申请时间、手机号、行程时间、行程数量、总金额、每条行程的详细信息

返回格式：
{
    "success": true/false,
    "platform": "高德地图",
    "filename": "文件名",
    "basic_info": {
        "apply_time": "申请时间",
        "phone": "手机号",
        "trip_start_time": "行程开始时间",
        "trip_end_time": "行程结束时间",
        "trip_count": 行程数量,
        "total_amount": 总金额
    },
    "trips": [
        {
            "序号": "1",
            "服务商": "服务商名称",
            "车型": "车型",
            "上车时间": "2024-06-19 12:32",
            "城市": "北京市",
            "起点": "起点地址",
            "终点": "终点地址",
            "金额(元)": "53.89"
        }
    ]
}
"""

import os
import re
import json
import logging
import sys
from typing import Dict, List, Any, Optional, Tuple

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 尝试导入 pymupdf
try:
    import pymupdf
except ImportError:
    logger.error("未安装 pymupdf，请运行: pip install pymupdf")
    sys.exit(1)


def is_gaode_itinerary(pdf_path: str) -> bool:
    """判断是否为高德打车行程单"""
    doc = None
    try:
        doc = pymupdf.open(pdf_path)
        page = doc[0]
        text = page.get_text()
        if '高德地图' in text or 'AMAP ITINERARY' in text or '高德打车' in text:
            return True
        return False
    except Exception as e:
        logger.warning(f"判断文件类型失败: {e}")
        return False
    finally:
        if doc:
            doc.close()


def extract_text_with_smart_merge(pdf_path: str, trip_count: int = 0) -> str:
    """使用pymupdf的布局分析提取文本，根据像素距离智能合并"""
    doc = None
    try:
        doc = pymupdf.open(pdf_path)
        page = doc[0]
        layout = page.get_text('dict')
        blocks = layout.get('blocks', [])
        
        text_spans = []
        for block in blocks:
            if 'lines' in block:
                for line in block['lines']:
                    if 'spans' in line:
                        for span in line['spans']:
                            text = span.get('text', '').strip()
                            if text:
                                bbox = span.get('bbox', [])
                                if len(bbox) >= 4:
                                    text_spans.append({
                                        'text': text,
                                        'x0': bbox[0],
                                        'y0': bbox[1],
                                        'x1': bbox[2],
                                        'y1': bbox[3],
                                        'font_size': span.get('size', 10)
                                    })
        
        if not text_spans:
            return ""
        
        avg_font_size = sum(s['font_size'] for s in text_spans) / len(text_spans)
        y_threshold = avg_font_size * 1.5
        x_threshold = 50
        
        y_groups = {}
        for span in text_spans:
            y_group = round(span['y0'] / y_threshold) * y_threshold
            if y_group not in y_groups:
                y_groups[y_group] = []
            y_groups[y_group].append(span)
        
        merged_lines = []
        for y_group in sorted(y_groups.keys()):
            spans = sorted(y_groups[y_group], key=lambda s: s['x0'])
            line_parts = []
            current_line = []
            
            for span in spans:
                if not current_line:
                    current_line.append(span)
                else:
                    prev_span = current_line[-1]
                    x_gap = span['x0'] - prev_span['x1']
                    y_diff = abs(span['y0'] - prev_span['y0'])
                    
                    if x_gap < x_threshold and y_diff < y_threshold:
                        current_line.append(span)
                    else:
                        if current_line:
                            line_parts.append(current_line)
                        current_line = [span]
            
            if current_line:
                line_parts.append(current_line)
            
            for line_part in line_parts:
                line_part.sort(key=lambda s: s['x0'])
                merged_text = ""
                for i, span in enumerate(line_part):
                    if i > 0:
                        prev_span = line_part[i-1]
                        x_gap = span['x0'] - prev_span['x1']
                        if x_gap > 5:
                            merged_text += " " + span['text']
                        else:
                            merged_text += span['text']
                    else:
                        merged_text = span['text']
                merged_lines.append(merged_text)
        
        full_text = "\n".join(merged_lines)
        if full_text.strip():
            logger.info(f"使用pymupdf布局分析成功提取文本")
            return full_text
            
    except Exception as e:
        logger.warning(f"使用pymupdf布局分析提取文本失败: {e}")
    finally:
        if doc:
            doc.close()
    
    return ""


def extract_start_end_with_coordinates_optimized(
    row_y: float,
    start_x0: float, start_x1: float,
    end_x0: float, end_x1: float,
    all_text_spans: List[Dict],
    y_threshold: float
) -> Tuple[str, str]:
    """
    使用坐标信息提取起点和终点，处理换行情况
    策略：
    1. 找到当前行的Y坐标
    2. 检查当前行及上下各3行（最多7行），合并起点/终点列的文本
    3. 按Y坐标排序后合并
    """
    start_texts = []
    end_texts = []
    
    row_y_rounded = round(row_y / y_threshold) * y_threshold
    
    # 检查当前行及上下各3行（用于处理最多3行的换行文本）
    for span in all_text_spans:
        span_y_rounded = round(span['y0'] / y_threshold) * y_threshold
        y_diff = abs(span_y_rounded - row_y_rounded)
        
        # 只检查Y坐标相近的行（上下各3行范围内，即最多7行）
        if y_diff > y_threshold * 3:
            continue
        
        text = span['text']
        center_x = span['center_x']
        
        # 过滤无关文本
        if text in ['起点', '终点', '序号', '服务商', '车型', '上车时间', '城市', '金额(元)', '说明：', '页码：']:
            continue
        if text.isdigit() and len(text) <= 2:  # 过滤序号
            continue
        if re.match(r'^\d{4}-\d{2}-\d{2}', text):  # 过滤日期
            continue
        if re.match(r'^[\d.]+元$', text):  # 过滤金额
            continue
        if text in ['北京市', '上海市', '广州市', '深圳市', '杭州市', '成都市', '武汉市', '西安市', '南京市', '重庆市']:
            continue
        if text in ['T3出行', '经济型']:  # 过滤服务商和车型
            continue
        
        # 检查是否在起点列范围内
        if start_x0 - 20 <= center_x <= start_x1 + 20:
            start_texts.append((span['y0'], text))
        # 检查是否在终点列范围内
        elif end_x0 - 20 <= center_x <= end_x1 + 20:
            end_texts.append((span['y0'], text))
    
    # 按Y坐标排序并合并
    start_point = ""
    if start_texts:
        start_texts.sort(key=lambda x: x[0])
        start_point = ' '.join([t[1] for t in start_texts])
    
    end_point = ""
    if end_texts:
        end_texts.sort(key=lambda x: x[0])
        end_point = ' '.join([t[1] for t in end_texts])
    
    return start_point, end_point


def extract_start_end_by_columns_optimized(
    row_y: float,
    row_idx: int,
    header_columns: Dict[str, Tuple[float, float]], 
    y_groups: Dict[float, List], 
    sorted_y: List[float],
    data_rows: List[Tuple[float, List]]
) -> Tuple[str, str]:
    """优化版：根据列定义提取起点和终点，更精确地处理换行"""
    try:
        if '起点' not in header_columns or '终点' not in header_columns:
            return "", ""
        
        start_x0, start_x1 = header_columns['起点']
        end_x0, end_x1 = header_columns['终点']
        
        start_texts = []
        end_texts = []
        
        # 获取当前行的Y坐标索引
        row_index = None
        for i, y in enumerate(sorted_y):
            if abs(y - row_y) < 5:
                row_index = i
                break
        
        if row_index is None:
            return "", ""
        
        # 只检查当前行和下一行（如果下一行存在且不是新的数据行）
        for offset in [0, 1]:
            check_index = row_index + offset
            if check_index >= len(sorted_y):
                break
                
            check_y = sorted_y[check_index]
            items = y_groups[check_y]
            
            # 如果检查下一行，需要确认它不是新的数据行
            if offset == 1:
                # 检查下一行是否在data_rows中（即是否有序号）
                is_data_row = False
                for data_y, data_items in data_rows:
                    if abs(data_y - check_y) < 5:
                        # 检查是否有序号
                        if '序号' in header_columns:
                            seq_x0, seq_x1 = header_columns['序号']
                            for item in data_items:
                                if item['text'].isdigit() and len(item['text']) <= 2:
                                    if seq_x0 - 20 <= item['center_x'] <= seq_x1 + 20:
                                        is_data_row = True
                                        break
                        if is_data_row:
                            break
                if is_data_row:
                    break  # 下一行是新数据行，不合并
            
            # 提取这一行的起点和终点文本
            for item in items:
                center_x = item['center_x']
                text = item['text']
                # 过滤掉表头文字和无关文本
                if text in ['起点', '终点', '序号', '服务商', '车型', '上车时间', '城市', '金额(元)', '说明：', '页码：']:
                    continue
                # 过滤掉数字序号（1、2、3等）
                if text.isdigit() and len(text) <= 2:
                    continue
                # 过滤掉日期时间格式
                if re.match(r'^\d{4}-\d{2}-\d{2}', text):
                    continue
                # 过滤掉金额格式
                if re.match(r'^[\d.]+元$', text):
                    continue
                # 过滤掉城市名称
                if text in ['北京市', '上海市', '广州市', '深圳市', '杭州市', '成都市', '武汉市', '西安市', '南京市', '重庆市']:
                    continue
                
                if start_x0 - 20 <= center_x <= start_x1 + 20:
                    start_texts.append((item['y0'], text))
                elif end_x0 - 20 <= center_x <= end_x1 + 20:
                    end_texts.append((item['y0'], text))
        
        start_point = ""
        end_point = ""
        
        if start_texts:
            start_texts.sort(key=lambda x: x[0])
            start_point = ' '.join([t[1] for t in start_texts])
        
        if end_texts:
            end_texts.sort(key=lambda x: x[0])
            end_point = ' '.join([t[1] for t in end_texts])
        
        return start_point, end_point
        
    except Exception as e:
        logger.warning(f"提取起点终点失败: {e}")
        return "", ""


def extract_start_end_by_columns(
    pdf_path: str, 
    row_y: float, 
    header_columns: Dict[str, Tuple[float, float]], 
    y_groups: Dict[float, List], 
    sorted_y: List[float]
) -> Tuple[str, str]:
    """根据列定义提取起点和终点，处理换行情况"""
    try:
        if '起点' not in header_columns or '终点' not in header_columns:
            return "", ""
        
        start_x0, start_x1 = header_columns['起点']
        end_x0, end_x1 = header_columns['终点']
        
        start_texts = []
        end_texts = []
        
        row_index = None
        for i, y in enumerate(sorted_y):
            if abs(y - row_y) < 5:
                row_index = i
                break
        
        if row_index is None:
            return "", ""
        
        # 只检查当前行及紧邻的下一行（用于处理换行），避免跨行污染
        # 首先找到当前行的序号位置，用于判断哪些行属于同一行程
        current_seq_y = None
        if '序号' in header_columns:
            seq_x0, seq_x1 = header_columns['序号']
            for item in y_groups[sorted_y[row_index]]:
                if item['text'].isdigit() and len(item['text']) <= 2:
                    if seq_x0 - 20 <= item['center_x'] <= seq_x1 + 20:
                        current_seq_y = item['y0']
                        break
        
        # 检查当前行及后续行（直到遇到新的序号或没有更多相关文本）
        # 最多检查3行（当前行+后续2行），避免无限循环
        max_check = min(3, len(sorted_y) - row_index)
        
        for offset in range(max_check):
            check_index = row_index + offset
            if check_index >= len(sorted_y):
                break
                
            check_y = sorted_y[check_index]
            items = y_groups[check_y]
            
            # 检查当前行是否有新的序号（除了第一行，其他行如果有序号说明是新行程）
            if offset > 0:
                has_new_seq = False
                if '序号' in header_columns:
                    seq_x0, seq_x1 = header_columns['序号']
                    for item in items:
                        if item['text'].isdigit() and len(item['text']) <= 2:
                            if seq_x0 - 20 <= item['center_x'] <= seq_x1 + 20:
                                has_new_seq = True
                                break
                if has_new_seq:
                    break  # 遇到新行程，停止合并
            
            # 检查这一行在起点/终点列是否有文本
            has_start_text = False
            has_end_text = False
            for item in items:
                center_x = item['center_x']
                if start_x0 - 20 <= center_x <= start_x1 + 20:
                    has_start_text = True
                if end_x0 - 20 <= center_x <= end_x1 + 20:
                    has_end_text = True
            
            # 如果这一行在起点/终点列都没有文本，且不是当前行，则停止检查
            if offset > 0 and not has_start_text and not has_end_text:
                break
            
            # 提取这一行的起点和终点文本
            for item in items:
                center_x = item['center_x']
                text = item['text']
                # 过滤掉表头文字和无关文本
                if text in ['起点', '终点', '序号', '服务商', '车型', '上车时间', '城市', '金额(元)', '说明：', '页码：']:
                    continue
                # 过滤掉数字序号（1、2、3等）
                if text.isdigit() and len(text) <= 2:
                    continue
                # 过滤掉日期时间格式
                if re.match(r'^\d{4}-\d{2}-\d{2}', text):
                    continue
                # 过滤掉金额格式
                if re.match(r'^[\d.]+元$', text):
                    continue
                # 过滤掉城市名称（应该在城市列）
                if text in ['北京市', '上海市', '广州市', '深圳市', '杭州市', '成都市', '武汉市', '西安市', '南京市', '重庆市']:
                    continue
                
                if start_x0 - 20 <= center_x <= start_x1 + 20:
                    start_texts.append((item['y0'], text))
                elif end_x0 - 20 <= center_x <= end_x1 + 20:
                    end_texts.append((item['y0'], text))
        
        start_point = ""
        end_point = ""
        
        if start_texts:
            start_texts.sort(key=lambda x: x[0])
            start_point = ' '.join([t[1] for t in start_texts])
        
        if end_texts:
            end_texts.sort(key=lambda x: x[0])
            end_point = ' '.join([t[1] for t in end_texts])
        
        return start_point, end_point
        
    except Exception as e:
        logger.warning(f"提取起点终点失败: {e}")
        return "", ""


def parse_trips_by_coordinates(pdf_path: str, trip_count: int) -> List[Dict[str, Any]]:
    """
    根据XY坐标解析行程数据 - 优化版
    策略：
    1. 使用纯文本(page.get_text())识别表格行结构（每列一行）
    2. 使用坐标信息精确合并起点和终点的换行文本
    """
    trips = []
    doc = None
    try:
        doc = pymupdf.open(pdf_path)
        page = doc[0]
        
        # 1. 获取纯文本（用于识别表格行）
        plain_text = page.get_text()
        lines = plain_text.split('\n')
        
        # 2. 获取坐标信息（用于合并起点和终点的换行文本）
        layout = page.get_text('dict')
        blocks = layout.get('blocks', [])
        
        # 提取所有文本块及其坐标
        all_text_spans = []
        for block in blocks:
            if 'lines' in block:
                for line in block['lines']:
                    if 'spans' in line:
                        for span in line['spans']:
                            text = span.get('text', '').strip()
                            bbox = span.get('bbox', [])
                            if text and len(bbox) >= 4:
                                all_text_spans.append({
                                    'text': text,
                                    'x0': bbox[0],
                                    'y0': bbox[1],
                                    'x1': bbox[2],
                                    'y1': bbox[3],
                                    'center_x': (bbox[0] + bbox[2]) / 2,
                                    'center_y': (bbox[1] + bbox[3]) / 2,
                                })
        
        # 3. 识别表头各列的X坐标范围（用于定位起点和终点列）
        header_columns = {}
        y_threshold = 5
        
        # 找到所有表头文本块
        header_keywords = ['序号', '服务商', '车型', '上车时间', '城市', '起点', '终点', '金额']
        header_spans = []
        for span in all_text_spans:
            text = span['text']
            if any(keyword in text for keyword in header_keywords):
                header_spans.append(span)
        
        # 按X坐标排序，识别各列
        header_spans.sort(key=lambda x: x['center_x'])
        
        # 识别各列的X坐标范围
        for span in header_spans:
            text = span['text']
            if '序号' in text and '序号' not in header_columns:
                header_columns['序号'] = (span['x0'], span['x1'])
            elif '服务商' in text and '服务商' not in header_columns:
                header_columns['服务商'] = (span['x0'], span['x1'])
            elif '车型' in text and '车型' not in header_columns:
                header_columns['车型'] = (span['x0'], span['x1'])
            elif '上车时间' in text and '上车时间' not in header_columns:
                header_columns['上车时间'] = (span['x0'], span['x1'])
            elif any(c in text for c in ['城市', '北京市', '杭州市']) and '城市' not in header_columns:
                header_columns['城市'] = (span['x0'], span['x1'])
            elif '起点' in text and '起点' not in header_columns:
                header_columns['起点'] = (span['x0'], span['x1'])
            elif '终点' in text and '终点' not in header_columns:
                header_columns['终点'] = (span['x0'], span['x1'])
            elif '金额' in text and '金额' not in header_columns:
                header_columns['金额'] = (span['x0'], span['x1'])
        
        if '起点' not in header_columns or '终点' not in header_columns:
            logger.warning(f"未找到起点或终点列，已找到的列: {list(header_columns.keys())}")
            return []
        
        start_x0, start_x1 = header_columns['起点']
        end_x0, end_x1 = header_columns['终点']
        
        # 4. 从纯文本中识别数据行（每列占一行，但起点和终点可能换行）
        trip_index = 0
        i = 0
        
        while i < len(lines) and trip_index < trip_count:
            line = lines[i].strip()
            
            if not line or '说明：' in line or '页码：' in line:
                i += 1
                continue
            
            # 查找以数字开头的行（序号行，新行程开始）
            seq_match = re.match(r'^(\d+)$', line)
            if not seq_match:
                i += 1
                continue
            
            seq_num = seq_match.group(1)
            seq_line_index = i
            
            # 从序号行开始，动态读取后续列
            i += 1
            if i >= len(lines):
                break
            
            service = lines[i].strip() if i < len(lines) else ""
            i += 1
            if i >= len(lines):
                break
            
            car_type = lines[i].strip() if i < len(lines) else ""
            i += 1
            if i >= len(lines):
                break
            
            # 查找日期时间行
            date_time = None
            while i < len(lines):
                date_match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})', lines[i])
                if date_match:
                    date_time = date_match.group(1)
                    i += 1
                    break
                i += 1
            
            if not date_time or i >= len(lines):
                i = seq_line_index + 1
                continue
            
            # 查找城市行
            city = ""
            while i < len(lines):
                city_line = lines[i].strip()
                city_match = re.search(r'(北京市|上海市|广州市|深圳市|杭州市|成都市|武汉市|西安市|南京市|重庆市)', city_line)
                if city_match:
                    city = city_match.group(1)
                    i += 1
                    break
                i += 1
            
            if i >= len(lines):
                i = seq_line_index + 1
                continue
            
            # 查找金额行（作为终点和起点的结束标记）
            amount = None
            amount_line_index = -1
            for j in range(i, min(i + 10, len(lines))):  # 最多向前查找10行
                amount_match = re.search(r'([\d.]+)元', lines[j])
                if amount_match:
                    amount = amount_match.group(1)
                    amount_line_index = j
                    break
            
            if not amount:
                i = seq_line_index + 1
                continue
            
            # 5. 使用坐标信息提取起点和终点（包括换行文本）
            # 找到当前行序号的Y坐标
            seq_y = None
            for span in all_text_spans:
                if span['text'] == seq_num:
                    seq_y = round(span['y0'] / y_threshold) * y_threshold
                    break
            
            if seq_y is None:
                i = amount_line_index + 1
                continue
            
            # 提取起点和终点（使用坐标信息合并换行文本）
            start_point, end_point = extract_start_end_with_coordinates_optimized(
                seq_y,
                start_x0, start_x1,
                end_x0, end_x1,
                all_text_spans,
                y_threshold
            )
            
            trip = {
                "序号": seq_num,
                "服务商": service,
                "车型": car_type,
                "上车时间": date_time,
                "城市": city,
                "起点": start_point,
                "终点": end_point,
                "金额(元)": amount
            }
            
            trips.append(trip)
            trip_index += 1
            logger.info(f"✅ 坐标解析行程 {seq_num}: {amount}元")
            
            # 跳到金额行之后
            i = amount_line_index + 1
        
        return trips
        
    except Exception as e:
        logger.error(f"根据坐标解析行程数据失败: {e}", exc_info=True)
        return []
    finally:
        if doc:
            doc.close()


def parse_gaode_itinerary_enhanced(pdf_path: str) -> Dict[str, Any]:
    """
    解析高德打车PDF行程单 - 增强版
    """
    if not os.path.exists(pdf_path):
        return {"success": False, "error": f"文件不存在: {pdf_path}"}
    
    try:
        # 1. 判断是否为高德行程单
        if not is_gaode_itinerary(pdf_path):
            return {"success": False, "error": "不是高德打车行程单"}
        
        # 2. 提取基本信息
        doc = pymupdf.open(pdf_path)
        page = doc[0]
        basic_text = page.get_text()
        doc.close()
        
        result = {
            "success": True,
            "platform": "高德地图",
            "filename": os.path.basename(pdf_path),
            "basic_info": {},
            "trips": []
        }
        
        apply_time_match = re.search(r'申请时间[：:]\s*(\d{4}-\d{2}-\d{2})', basic_text)
        if apply_time_match: result["basic_info"]["apply_time"] = apply_time_match.group(1)
        
        phone_match = re.search(r'行程人手机号[：:]\s*(\d{11})', basic_text)
        if phone_match: result["basic_info"]["phone"] = phone_match.group(1)
        
        time_range_match = re.search(r'行程时间[：:]\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})至(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})', basic_text)
        if time_range_match:
            result["basic_info"]["trip_start_time"] = time_range_match.group(1)
            result["basic_info"]["trip_end_time"] = time_range_match.group(2)
        
        trip_count = 0
        trip_count_match = re.search(r'共计(\d+)单?行程', basic_text)
        if trip_count_match:
            trip_count = int(trip_count_match.group(1))
            result["basic_info"]["trip_count"] = trip_count
        
        amount_match = re.search(r'合计[：:]?\s*(\d+\.\d{2})元', basic_text)
        if amount_match: result["basic_info"]["total_amount"] = float(amount_match.group(1))
        
        logger.info(f"📊 基本信息：行程数量={trip_count}, 总金额={result['basic_info'].get('total_amount', 0)}元")
        
        # 3. 使用XY坐标方法解析行程数据（优先）
        result["trips"] = parse_trips_by_coordinates(pdf_path, trip_count)
        
        # 4. 如果坐标方法失败，回退到文本解析方法
        if not result["trips"]:
            logger.warning("坐标方法解析失败或为空，回退到文本解析方法")
            
            text = extract_text_with_smart_merge(pdf_path, trip_count)
            lines = text.split('\n')
            
            header_line_index = -1
            for i, line in enumerate(lines):
                if '序号' in line and ('服务商' in line or '金额' in line):
                    header_line_index = i
                    break
            
            if header_line_index >= 0:
                i = header_line_index + 1
                trip_index = 0
                
                while i < len(lines) and trip_index < trip_count:
                    line = lines[i].strip()
                    
                    if not line or '说明：' in line or '页码：' in line:
                        i += 1
                        continue
                    
                    # 查找以数字开头的行
                    seq_match = re.match(r'^(\d+)', line)
                    if seq_match:
                        seq_num = seq_match.group(1)
                        full_line = line
                        
                        # 尝试合并下一行（如果当前行没金额）
                        if not re.search(r'[\d.]+元', line) and i + 1 < len(lines):
                            next_line = lines[i + 1].strip()
                            if re.search(r'[\d.]+元', next_line):
                                full_line = line + ' ' + next_line
                                i += 1 # 跳过已被合并的行
                        
                        remaining = full_line[len(seq_num):].strip()
                        date_match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})', remaining)
                        
                        if not date_match:
                            i += 1
                            continue
                            
                        date_time = date_match.group(1)
                        date_pos = remaining.find(date_time)
                        
                        before_date = remaining[:date_pos].strip()
                        after_date = remaining[date_pos + len(date_time):].strip()
                        
                        parts_before = before_date.split()
                        service = parts_before[0] if parts_before else ""
                        car_type = ' '.join(parts_before[1:]) if len(parts_before) > 1 else ""
                        
                        amount_match = re.search(r'([\d.]+)元', after_date)
                        amount = amount_match.group(1) if amount_match else ""
                        
                        if not amount:
                            i += 1
                            continue
                            
                        if amount_match:
                            after_date = after_date[:amount_match.start()].strip()
                        
                        city_match = re.search(r'(北京市|上海市|广州市|深圳市|杭州市|成都市|武汉市|西安市|南京市|重庆市)', after_date)
                        city = city_match.group(1) if city_match else ""
                        
                        # 获取起点终点（文本分割回退策略）
                        start_point = ""
                        end_point = ""
                        if city:
                            city_pos = after_date.find(city)
                            if city_pos >= 0:
                                locations_text = after_date[city_pos + len(city):].strip()
                                if '  ' in locations_text:
                                    parts = locations_text.split('  ', 1)
                                    start_point = parts[0].strip()
                                    end_point = parts[1].strip() if len(parts) > 1 else ""
                                elif ' ' in locations_text:
                                    parts = locations_text.split()
                                    if len(parts) >= 2:
                                        mid = len(parts) // 2
                                        start_point = ' '.join(parts[:mid]).strip()
                                        end_point = ' '.join(parts[mid:]).strip()
                                    else:
                                        start_point = locations_text
                                else:
                                    start_point = locations_text
                        
                        trip = {
                            "序号": seq_num,
                            "服务商": service,
                            "车型": car_type,
                            "上车时间": date_time,
                            "城市": city,
                            "起点": start_point,
                            "终点": end_point,
                            "金额(元)": amount
                        }
                        
                        result["trips"].append(trip)
                        trip_index += 1
                    
                    i += 1

        if not result["trips"]:
            result["warning"] = "未能解析到行程表格数据"
        else:
            logger.info(f"✅ 总计成功解析 {len(result['trips'])} 条行程记录")

        return result

    except Exception as e:
        logger.error(f"解析PDF全局失败: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python trip_table_parse_enhanced.py <pdf_file_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    result = parse_gaode_itinerary_enhanced(pdf_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))

