# 视障人士智能辅助工具Flask后端实现计划

## 项目概述
为视障人士开发的智能辅助工具后端，基于Flask框架，集成YOLOv8目标检测、IP定位、紧急联系人呼叫和智能问答功能。

## 实现步骤

### 1. 创建基础Flask应用结构
- 初始化Flask应用
- 添加主页路由用于服务器状态测试

### 2. 实现YOLOv8目标检测功能
- 加载预训练YOLOv8模型
- 创建`POST /detect`端点接收ESP32上传的图像
- 使用OpenCV读取和预处理图像
- 运行YOLOv8推理检测道路关键目标
- 分析检测结果，生成语音播报文本
- 返回JSON格式的检测结果和描述文本

### 3. 实现IP定位功能
- 创建`GET /location`端点
- 获取请求方公网IP地址
- 调用ip-api.com获取地理位置信息
- 返回JSON格式的位置数据

### 4. 实现紧急联系人呼叫功能
- 创建`POST /emergency`端点
- 集成Twilio API发送求助短信
- 包含当前位置信息
- 返回成功响应

### 5. 实现智能问答功能
- 创建`POST /ask`端点接收文本问题
- 集成OpenAI API（示例）
- 添加位置上下文信息
- 返回JSON格式的回答

### 6. 生成依赖文件
- 创建`requirements.txt`包含所有必要库

## 代码结构
```
├── app.py          # 主Flask应用文件
└── requirements.txt # 项目依赖
```

## 关键技术点
- YOLOv8模型加载和推理
- OpenCV图像处理
- 第三方API集成（IP定位、Twilio、OpenAI）
- 响应式JSON格式设计
- 语音播报文本生成逻辑

## 测试要点
- 使用Postman或curl测试各API端点
- 确保YOLOv8模型正确加载和检测
- 验证IP定位准确性
- 测试紧急联系人短信发送
- 验证智能问答功能

## 环境配置
- Python 3.8+
- 安装依赖：`pip install -r requirements.txt`
- 下载YOLOv8模型：`yolov8n.pt`
- 替换API密钥占位符

## 预期结果
- 完整可运行的Flask后端应用
- 清晰的API设计和注释
- 可扩展的代码结构
- 满足所有功能需求的实现