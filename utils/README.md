# 打印机工具模块 (Printer Utils)

这个模块提供了获取系统中可用打印机信息的功能，基于CUPS (Common Unix Printing System) 实现。

## 功能特性

- 🖨️ 获取所有可用的打印机列表
- 📊 显示打印机的详细状态信息
- ⭐ 识别默认打印机
- 🔍 根据名称查询特定打印机
- 📝 友好的控制台输出格式
- 🧪 完整的测试脚本

## 文件说明

- `printer_utils.py` - 主要的打印机工具模块
- `test_printer_utils.py` - 测试脚本
- `README.md` - 使用说明文档

## 使用方法

### 1. 直接运行

```bash
# 在utils目录下运行
cd utils
python3 printer_utils.py
```

### 2. 作为模块导入

```python
from printer_utils import PrinterUtils

# 创建实例
printer_utils = PrinterUtils()

# 获取所有打印机
printers = printer_utils.get_available_printers()

# 获取默认打印机
default_printer = printer_utils.get_default_printer()

# 根据名称获取打印机
printer_info = printer_utils.get_printer_by_name("打印机名称")

# 打印摘要信息
printer_utils.print_printer_summary()
```

### 3. 运行测试

```bash
cd utils
python3 test_printer_utils.py
```

## 打印机信息字段

每个打印机对象包含以下信息：

- `name`: 打印机名称
- `state`: 打印机状态（空闲、打印中、停止等）
- `state_message`: 状态详细信息
- `info`: 打印机描述信息
- `location`: 打印机位置
- `is_accepting`: 是否接受打印任务
- `uri`: 打印机URI
- `driver`: 打印机驱动信息
- `default`: 是否为默认打印机

## 状态码说明

- `3`: 空闲
- `4`: 打印中
- `5`: 停止
- `6`: 离线
- `7`: 暂停
- `8`: 错误
- `9`: 维护中
- `10-20`: 各种等待状态

## 依赖要求

- Python 3.6+
- pycups (已在项目requirements.txt中)
- CUPS系统服务

## 注意事项

1. 此工具需要在Linux系统上运行
2. 需要CUPS服务正在运行
3. 用户需要有访问CUPS的权限
4. 如果CUPS连接失败，会记录错误日志

## 错误处理

模块包含完整的错误处理机制：

- CUPS连接失败时会记录错误
- 获取打印机信息失败时会返回空列表
- 所有异常都会被捕获并记录到日志中

## 示例输出

```
🖨️  发现 2 台打印机:
================================================================================

1. ⭐ HP-LaserJet-Pro-M404n
   状态: 空闲
   接受任务: ✅
   描述: HP LaserJet Pro M404n
   位置: 办公室
   驱动: HP LaserJet Pro M404n

2.    Canon-PIXMA-MG3600
   状态: 离线
   接受任务: ❌
   描述: Canon PIXMA MG3600
   位置: 会议室
   驱动: Canon PIXMA MG3600

================================================================================
⭐ 默认打印机: HP-LaserJet-Pro-M404n
```
