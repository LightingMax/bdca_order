# 智能PDF打印功能说明

## 功能概述

智能PDF打印功能解决了多页PDF（特别是行程单）的打印问题。当PDF超过2页时，系统会自动识别文件类型并进行智能处理。

## 核心特性

### 1. 自动PDF分析
- **页数检测**：使用 `pdfinfo` 命令获取PDF页数
- **类型识别**：自动识别PDF是行程单还是发票
- **智能判断**：根据页数和类型决定打印策略

### 2. 智能打印策略

#### 2.1 普通PDF（≤2页）
- 直接使用CUPS打印
- 无需特殊处理

#### 2.2 多页行程单（>2页）
- **第一页**：尝试与对应发票合并打印
- **剩余页面**：正常打印行程单的第2页开始

#### 2.3 回退机制
- 如果合并失败，回退到直接打印
- 如果找不到对应发票，直接打印

### 3. 文件匹配逻辑
- 通过文件名中的关键词匹配行程单和发票
- 支持的模式：`\d+个行程`、`订单\d+`、`trip\d+`
- 在临时目录中查找对应文件

## 技术实现

### 依赖工具
- **pdfinfo**：获取PDF页数信息
- **pdftk**：PDF页面提取和合并
- **CUPS**：实际打印执行

### 核心函数

#### `get_pdf_page_count(file_path)`
```python
def get_pdf_page_count(file_path: str) -> int:
    """获取PDF文件的页数"""
    # 使用pdfinfo命令解析页数
```

#### `identify_pdf_type(filename)`
```python
def identify_pdf_type(filename: str) -> str:
    """识别PDF文件类型（行程单或发票）"""
    # 通过文件名关键词判断类型
```

#### `create_combined_first_page(itinerary_path, invoice_path, output_path)`
```python
def create_combined_first_page(itinerary_path: str, invoice_path: str, output_path: str) -> bool:
    """创建第一页合并版本（行程单+发票）"""
    # 使用pdftk合并第一页
```

#### `smart_print_pdf(printer_name, file_path, print_options)`
```python
def smart_print_pdf(printer_name: str, file_path: str, print_options: dict) -> bool:
    """智能PDF打印 - 处理多页PDF的特殊情况"""
    # 核心智能打印逻辑
```

## API端点

### 1. 智能打印
```
POST /print?printer_name={printer_name}
```
- 自动检测PDF页数和类型
- 根据情况选择最佳打印策略

### 2. PDF分析
```
POST /analyze-pdf
```
- 分析PDF文件信息
- 返回页数、类型等详细信息

## 使用示例

### 测试脚本
```bash
# 测试PDF分析
python test_smart_print.py test.pdf

# 测试智能打印
# 通过API自动调用
```

### 文件命名规范
为了正确匹配行程单和发票，建议使用以下命名格式：

**行程单**：
- `阳光出行-32.13元-3个行程-行程单.pdf`
- `订单12345-行程单.pdf`
- `trip001-行程单.pdf`

**发票**：
- `阳光出行-32.13元-3个行程-发票.pdf`
- `订单12345-发票.pdf`
- `trip001-发票.pdf`

## 配置要求

### 系统依赖
```bash
# Ubuntu/Debian
sudo apt-get install poppler-utils pdftk

# CentOS/RHEL
sudo yum install poppler-utils pdftk

# 或者使用包管理器安装
```

### 环境变量
```bash
# 确保CUPS服务运行
sudo systemctl status cups

# 检查打印机状态
lpstat -p
```

## 错误处理

### 常见问题

1. **pdfinfo未找到**
   - 安装 `poppler-utils` 包
   - 确保命令在PATH中

2. **pdftk未找到**
   - 安装 `pdftk` 包
   - 某些系统可能需要额外配置

3. **PDF合并失败**
   - 检查文件权限
   - 验证PDF文件完整性
   - 查看日志获取详细错误信息

### 日志监控
```bash
# 查看服务日志
tail -f /var/log/cups/error_log

# 查看应用日志
# 在服务启动时查看控制台输出
```

## 性能优化

### 临时文件管理
- 自动清理临时文件
- 使用UUID避免文件名冲突
- 异常情况下确保清理

### 打印队列管理
- 支持打印任务状态查询
- 支持任务取消
- 错误重试机制

## 扩展功能

### 未来改进
1. **更多文件类型支持**：支持Word、Excel等格式
2. **智能布局优化**：根据内容自动调整页面布局
3. **批量处理**：支持多个文件同时处理
4. **打印预览**：在打印前预览合并效果

### 自定义配置
- 支持配置文件自定义匹配规则
- 支持自定义PDF处理策略
- 支持插件式扩展

## 故障排除

### 调试模式
```python
# 启用详细日志
logging.basicConfig(level=logging.DEBUG)

# 查看详细处理过程
logger.debug(f"处理详情: {details}")
```

### 测试建议
1. 先用小文件测试基本功能
2. 逐步测试多页PDF
3. 验证文件匹配逻辑
4. 检查打印输出质量

## 总结

智能PDF打印功能通过自动识别和智能处理，有效解决了多页行程单的打印问题。系统能够：

- 自动检测PDF特性
- 智能选择最佳打印策略
- 提供可靠的错误处理和回退机制
- 支持灵活的配置和扩展

这大大提升了打印服务的智能化和用户体验。

