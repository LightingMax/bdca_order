# 高德打车PDF行程单解析器

一个专门用于解析高德打车PDF行程单的Python工具，能够自动提取行程信息并返回结构化的JSON数据。

> **注意**：本工具专门针对**高德打车**的PDF行程单格式设计，不支持其他平台的行程单。

## 功能特性

- ✅ **智能布局识别**：基于pymupdf的XY坐标分析，准确识别表格结构
- ✅ **自动换行处理**：智能合并PDF中因换行而分散的文本（如起点、终点）
- ✅ **完整信息提取**：提取申请时间、手机号、行程时间、总金额等基本信息
- ✅ **详细行程解析**：解析每条行程的序号、服务商、车型、上车时间、城市、起点、终点、金额
- ✅ **容错机制**：坐标解析失败时自动回退到文本解析方法
- ✅ **JSON输出**：返回标准化的JSON格式数据，便于后续处理

## 安装要求

### 依赖库

```bash
pip install pymupdf
```

### Python版本

- Python 3.6+

## 使用方法

### 命令行使用

```bash
python trip_table_parse_enhanced.py <pdf_file_path>
```

示例：

```bash
python trip_table_parse_enhanced.py "path/to/高德打车电子行程单.pdf"
```

### 代码调用

```python
from trip_table_parse_enhanced import parse_gaode_itinerary_enhanced

# 或者如果放在子目录中
# from utils.trip_table_parse_enhanced import parse_gaode_itinerary_enhanced

# 解析PDF文件
result = parse_gaode_itinerary_enhanced("path/to/gaode_itinerary.pdf")

# 检查解析结果
if result["success"]:
    print(f"成功解析 {len(result['trips'])} 条行程")
    print(f"总金额: {result['basic_info']['total_amount']}元")
    
    # 遍历行程
    for trip in result["trips"]:
        print(f"行程 {trip['序号']}: {trip['起点']} -> {trip['终点']} ({trip['金额(元)']}元)")
else:
    print(f"解析失败: {result.get('error', '未知错误')}")
```

## 返回格式

### 成功返回示例

```json
{
  "success": true,
  "platform": "高德地图",
  "filename": "【高德打车-144.56元-3个行程】高德打车电子行程单.pdf",
  "basic_info": {
    "apply_time": "2024-07-01",
    "phone": "17353234569",
    "trip_start_time": "2024-06-19 12:32",
    "trip_end_time": "2024-06-21 09:21",
    "trip_count": 3,
    "total_amount": 144.56
  },
  "trips": [
    {
      "序号": "1",
      "服务商": "旅程易到",
      "车型": "旅程易到经济型",
      "上车时间": "2024-06-19 12:32",
      "城市": "北京市",
      "起点": "北京南站-东停车场M 层(夹层)-B2~B5通道",
      "终点": "航天智能院",
      "金额(元)": "53.89"
    },
    {
      "序号": "2",
      "服务商": "旅程易到",
      "车型": "旅程易到经济型",
      "上车时间": "2024-06-20 18:59",
      "城市": "北京市",
      "起点": "航天智能院",
      "终点": "汉庭优佳北京石景山首钢园酒店",
      "金额(元)": "16.12"
    }
  ]
}
```

### 失败返回示例

```json
{
  "success": false,
  "error": "不是高德打车行程单"
}
```

## 字段说明

### basic_info（基本信息）

| 字段 | 类型 | 说明 |
|------|------|------|
| apply_time | string | 申请时间（格式：YYYY-MM-DD） |
| phone | string | 行程人手机号 |
| trip_start_time | string | 行程开始时间（格式：YYYY-MM-DD HH:MM） |
| trip_end_time | string | 行程结束时间（格式：YYYY-MM-DD HH:MM） |
| trip_count | integer | 行程数量 |
| total_amount | float | 总金额（元） |

### trips（行程列表）

| 字段 | 类型 | 说明 |
|------|------|------|
| 序号 | string | 行程序号 |
| 服务商 | string | 服务商名称 |
| 车型 | string | 车型信息 |
| 上车时间 | string | 上车时间（格式：YYYY-MM-DD HH:MM） |
| 城市 | string | 城市名称 |
| 起点 | string | 起点地址（自动合并换行文本） |
| 终点 | string | 终点地址（自动合并换行文本） |
| 金额(元) | string | 行程金额（元） |

## 工作原理

1. **文件类型识别**：首先检查PDF是否为高德打车行程单
2. **基本信息提取**：使用正则表达式提取申请时间、手机号、行程数量、总金额等
3. **表格结构识别**：基于XY坐标识别表头行，确定各列的X坐标范围
4. **数据行解析**：识别包含序号、日期时间或金额的数据行
5. **列数据提取**：根据X坐标范围提取各列数据
6. **换行处理**：对于起点和终点，检查相邻行（上下各2行）以合并换行文本
7. **容错回退**：如果坐标解析失败，自动回退到基于文本的解析方法

## 注意事项

- ⚠️ **仅支持高德打车**：本工具专门针对高德打车PDF行程单格式设计，不支持其他平台（如滴滴、美团等）
- ✅ **自动换行处理**：对于PDF中因换行而分散的文本（如起点、终点），工具会自动合并
- ✅ **多服务商支持**：支持高德打车平台下的多种服务商（T3出行、旅程易到、如祺出行、飞嘀打车等）
- ⚠️ **格式变化**：如果高德打车PDF格式发生变化，可能需要调整解析逻辑
- 💡 **测试建议**：建议在使用前先测试几个样本文件，确保解析准确性

## 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。

## 贡献

欢迎提交 Issue 和 Pull Request！

## 更新日志

### v1.0.0 (当前版本)
- ✅ 初始版本发布
- ✅ 支持高德打车PDF行程单解析
- ✅ 基于XY坐标的智能布局识别
- ✅ 自动处理换行文本（起点、终点多行合并）
- ✅ JSON格式输出
- ✅ 支持多种服务商（T3出行、旅程易到、如祺出行、飞嘀打车等）
- ✅ 容错机制：坐标解析失败时自动回退到文本解析方法

