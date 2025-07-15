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
```
git clone https://github.com/yourusername/order_reimbursement.git
cd order_reimbursement
```

2. 安装依赖
```
pip install -r requirements.txt
```

3. 运行应用
```
python run.py
```

4. 在浏览器中访问 `http://localhost:5000`

## 目录结构

```
order_reimbursement/
├── app/                  # 应用主目录
│   ├── services/         # 服务模块
│   ├── static/           # 静态文件
│   ├── templates/        # HTML模板
│   ├── __init__.py       # 应用初始化
│   ├── config.py         # 配置文件
│   └── routes.py         # 路由定义
├── data/                 # 数据存储
├── temp/                 # 临时文件
├── requirements.txt      # 依赖列表
└── run.py                # 应用入口
```

## 使用说明

1. 在主页上传包含PDF和XML文件的ZIP压缩包
2. 系统会自动解压文件并识别订单相关的PDF和XML
3. 系统将匹配同一订单的行程单和发票，并合并为一个PDF
4. 用户可以预览合并后的PDF，或直接打印
5. 在"统计数据"页面可以查看所有用户的打印统计信息

## 注意事项

- 系统使用MAC地址识别用户，如果无法获取MAC地址，将使用IP和用户代理作为替代标识
- 打印功能需要系统支持相应的打印接口
- 在Windows系统上需要安装pywin32库以支持打印功能 