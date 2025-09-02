import cups

def get_hp_printer_trays():
    conn = cups.Connection()
    printer_name = "HP-LaserJet-MFP-M437-M443"
    
    try:
        # 获取打印机属性
        attrs = conn.getPrinterAttributes(printer_name)
        
        print("=== 打印机纸盘信息 ===")
        
        # 查找纸盘相关属性
        tray_keywords = ['inputslot', 'source', 'tray', 'media-source', 'input-tray']
        
        for key, value in attrs.items():
            key_lower = key.lower()
            if any(keyword in key_lower for keyword in tray_keywords):
                print(f"{key}: {value}")
        
        # 获取详细的打印机选项
        print("\n=== 可用的进纸选项 ===")
        ppd = conn.getPPD(printer_name)
        if ppd:
            with open(ppd, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # 查找InputSlot定义
                lines = content.split('\n')
                in_inputslot = False
                
                for line in lines:
                    if '*OpenUI *InputSlot' in line:
                        in_inputslot = True
                        print("找到进纸选项:")
                    elif '*CloseUI *InputSlot' in line:
                        in_inputslot = False
                    elif in_inputslot and line.startswith('*InputSlot'):
                        print(f"  {line}")
        
        # 获取当前设置
        print("\n=== 当前打印机设置 ===")
        options = conn.getPrinterAttributes(printer_name)
        if 'media-source-supported' in options:
            print(f"支持的进纸源: {options['media-source-supported']}")
            
    except cups.IPPError as e:
        print(f"CUPS错误: {e}")
    except Exception as e:
        print(f"其他错误: {e}")

# 运行查询
get_hp_printer_trays()