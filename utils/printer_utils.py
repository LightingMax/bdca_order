#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打印机工具模块
用于获取系统中可用的打印机信息
"""

import cups
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PrinterUtils:
    """打印机工具类"""
    
    def __init__(self):
        """初始化打印机工具"""
        self.conn = None
        self._init_cups_connection()
    
    def _init_cups_connection(self):
        """初始化CUPS连接"""
        try:
            self.conn = cups.Connection()
            logger.info("CUPS连接初始化成功")
        except Exception as e:
            logger.error(f"CUPS连接初始化失败: {e}")
            self.conn = None
    
    def get_available_printers(self) -> List[Dict[str, Any]]:
        """
        获取所有可用的打印机信息
        
        Returns:
            List[Dict[str, Any]]: 打印机信息列表
        """
        if not self.conn:
            logger.error("CUPS连接未初始化")
            return []
        
        try:
            printers = self.conn.getPrinters()
            logger.info(f"发现 {len(printers)} 台打印机")
            
            printer_list = []
            for printer_name, printer_info in printers.items():
                # 获取打印机状态码
                state_code = printer_info.get('printer-state', 0)
                
                # 使用硬编码逻辑判断是否接受任务，更可靠
                # 状态为3(空闲)或4(打印中)时认为可以接受任务
                is_accepting = state_code in [3, 4]
                
                printer_data = {
                    'name': printer_name,
                    'state': self._get_printer_state_text(state_code),
                    'state_message': printer_info.get('printer-state-message', ''),
                    'info': printer_info.get('printer-info', ''),
                    'location': printer_info.get('printer-location', ''),
                    'is_accepting': is_accepting,  # 使用硬编码逻辑
                    'uri': printer_info.get('printer-uri-supported', ''),
                    'driver': printer_info.get('printer-make-and-model', ''),
                    'default': printer_info.get('printer-is-default', False)
                }
                printer_list.append(printer_data)
            
            return printer_list
            
        except Exception as e:
            logger.error(f"获取打印机信息失败: {e}")
            return []
    
    def _get_printer_state_text(self, state_code: int) -> str:
        """
        将打印机状态码转换为可读文本
        
        Args:
            state_code (int): 打印机状态码
            
        Returns:
            str: 状态描述文本
        """
        state_map = {
            3: '空闲',
            4: '打印中',
            5: '停止',
            6: '离线',
            7: '暂停',
            8: '错误',
            9: '维护中',
            10: '等待',
            11: '处理中',
            12: '等待打印',
            13: '等待打印',
            14: '等待打印',
            15: '等待打印',
            16: '等待打印',
            17: '等待打印',
            18: '等待打印',
            19: '等待打印',
            20: '等待打印'
        }
        return state_map.get(state_code, f'未知状态({state_code})')
    
    def get_default_printer(self) -> Optional[Dict[str, Any]]:
        """
        获取默认打印机
        
        Returns:
            Optional[Dict[str, Any]]: 默认打印机信息，如果没有则返回None
        """
        printers = self.get_available_printers()
        for printer in printers:
            if printer.get('default', False):
                return printer
        return None
    
    def get_printer_by_name(self, printer_name: str) -> Optional[Dict[str, Any]]:
        """
        根据名称获取特定打印机信息
        
        Args:
            printer_name (str): 打印机名称
            
        Returns:
            Optional[Dict[str, Any]]: 打印机信息，如果没有找到则返回None
        """
        printers = self.get_available_printers()
        for printer in printers:
            if printer['name'] == printer_name:
                return printer
        return None
    
    def print_printer_summary(self):
        """打印打印机信息摘要到控制台"""
        printers = self.get_available_printers()
        
        if not printers:
            print("❌ 未找到可用的打印机")
            return
        
        print(f"\n🖨️  发现 {len(printers)} 台打印机:")
        print("=" * 80)
        
        for i, printer in enumerate(printers, 1):
            status_icon = "✅" if printer['is_accepting'] else "❌"
            default_icon = "⭐" if printer['default'] else "  "
            
            print(f"\n{i}. {default_icon} {printer['name']}")
            print(f"   状态: {printer['state']}")
            print(f"   接受任务: {status_icon}")
            
            if printer['info']:
                print(f"   描述: {printer['info']}")
            
            if printer['location']:
                print(f"   位置: {printer['location']}")
            
            if printer['driver']:
                print(f"   驱动: {printer['driver']}")
            
            if printer['state_message']:
                print(f"   状态信息: {printer['state_message']}")
        
        print("\n" + "=" * 80)
        
        # 显示默认打印机
        default_printer = self.get_default_printer()
        if default_printer:
            print(f"⭐ 默认打印机: {default_printer['name']}")
        else:
            print("⚠️  未设置默认打印机")


def main():
    """主函数 - 直接运行时的入口点"""
    print("🖨️  打印机信息查询工具")
    print(f"⏰ 查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        printer_utils = PrinterUtils()
        printer_utils.print_printer_summary()
        
    except Exception as e:
        print(f"❌ 程序执行出错: {e}")
        logger.error(f"程序执行出错: {e}")


if __name__ == "__main__":
    main()
