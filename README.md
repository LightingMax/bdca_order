# 订单报销系统

这是一个简单的网页系统，用于处理订单报销文件。系统可以解压ZIP文件，识别并匹配订单相关的PDF和XML文件，合并PDF文件，并自动调用打印机打印输出。

## 主要功能

- 解压用户上传的ZIP文件
- 识别并匹配订单相关的PDF和XML文件
- 合并PDF文件（行程单在前，发票在后）
- 调整合并后的PDF为适合打印的格式
- 自动调用打印机打印输出
- 记录用户打印信息并展示统计数据

## 技术栈

- **前端**：HTML, CSS, JavaScript, Bootstrap
- **后端**：Python + Flask
- **PDF处理**：PyPDF2
- **ZIP处理**：zipfile 库
- **XML解析**：xml.etree.ElementTree
- **打印功能**：cups 或 win32print (根据部署环境)
- **数据存储**：JSON文件

## 安装与运行

1. 克隆代码库
```bash
git clone https://github.com/yourusername/order_reimbursement.git
cd order_reimbursement
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置环境变量（可选）
```bash
# 复制环境变量示例文件
cp env.example .env

# 根据需要修改 .env 文件中的配置
# 特别是打印API服务的地址和认证信息
```

4. 运行应用

**方法一：使用启动脚本（推荐）**
```bash
python start_services.py
```

**方法二：手动启动两个服务**
```bash
# 终端1：启动打印API服务
python print_api_service_enhanced.py

# 终端2：启动主应用服务
python run.py
```

5. 在浏览器中访问 `http://localhost:12345`

6. 验证配置（可选）
```bash
# 测试配置和连接
python test/test_config.py
```

## 目录结构

```
order_reimbursement/
├── app/                  # 应用主目录
│   ├── services/         # 服务模块
│   │   ├── config_service.py  # 配置管理服务
│   │   ├── file_service.py    # 文件处理服务
│   │   ├── pdf_service.py     # PDF处理服务
│   │   └── print_service.py   # 打印服务
│   ├── static/           # 静态文件
│   ├── templates/        # HTML模板
│   ├── __init__.py       # 应用初始化
│   ├── config.py         # 配置文件
│   └── routes.py         # 路由定义
├── data/                 # 数据存储
├── temp/                 # 临时文件
├── test/                 # 测试工具
│   ├── test_config.py    # 配置测试工具
│   └── ...               # 其他测试文件
├── requirements.txt      # 依赖列表
├── env.example           # 环境变量示例
├── print_api_service_enhanced.py  # 增强版打印API服务
├── start_services.py     # 服务启动脚本
└── run.py                # 应用入口
```

## 使用说明

1. 在主页上传包含PDF和XML文件的ZIP压缩包
2. 系统会自动解压文件并识别订单相关的PDF和XML
3. 系统将匹配同一订单的行程单和发票，并合并为一个PDF
4. 用户可以预览合并后的PDF，或直接打印
5. 在"统计数据"页面可以查看所有用户的打印统计信息

## 配置架构

系统采用分层配置架构，确保配置的统一管理和灵活性：

### 配置层次
1. **环境变量** (最高优先级) - 通过 `.env` 文件或系统环境变量设置
2. **配置文件** (`app/config.py`) - 默认配置和配置结构定义
3. **配置服务** (`app/services/config_service.py`) - 统一的配置访问接口

### 主要配置项
- `PRINT_API_BASE_URL`: 打印API服务地址
- `PRINT_API_TOKEN`: 打印API认证令牌
- `DEFAULT_PRINTER_NAME`: 默认打印机名称
- `PRINT_API_TIMEOUT`: API请求超时时间

### 配置验证
使用 `python test/test_config.py` 可以验证配置的正确性和服务连接性。

## 注意事项

- 系统使用MAC地址识别用户，如果无法获取MAC地址，将使用IP和用户代理作为替代标识
- 打印功能需要系统支持相应的打印接口
- 在Windows系统上需要安装pywin32库以支持打印功能 