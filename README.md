# 视障人士智能辅助工具

## 项目概述

视障人士智能辅助工具是一个基于AI技术的出行辅助系统，专为视障人士设计。该系统通过ESP32-S3硬件设备采集摄像头图像，传输到后端服务器进行实时处理和分析，然后将结果以语音播报的形式反馈给用户，帮助视障人士感知周围环境，提高出行安全性和独立性。

## 功能介绍

### 1. 实时目标检测
- **功能**：识别道路上的关键目标，如行人、车辆、自行车、交通标志等
- **技术**：基于YOLOv8深度学习模型
- **应用**：生成语音播报文本，如"前方有行人"、"左前方检测到车辆"

### 2. IP定位
- **功能**：获取设备当前地理位置
- **技术**：基于IP地址的地理位置查询
- **应用**：语音播报当前位置，如"您当前在北京市附近"

### 3. 紧急联系人呼叫
- **功能**：一键发送求助信息给预设紧急联系人
- **技术**：集成Twilio短信服务
- **应用**：发送包含位置信息的求助短信，如"紧急求助：我可能在北京市附近遇到麻烦，请尽快联系我。"

### 4. 智能问答
- **功能**：基于大语言模型的智能问答
- **技术**：集成OpenAI API（示例）
- **应用**：回答用户问题，结合位置上下文，如"附近有超市吗？"

## 技术栈

### 后端
- **框架**：Flask 3.1.2
- **AI模型**：YOLOv8
- **图像处理**：OpenCV 4.12.0
- **HTTP请求**：Requests 2.32.5
- **短信服务**：Twilio 9.8.7
- **环境配置**：python-dotenv 1.2.1

### 前端
- **HTML5**：页面结构
- **CSS3**：样式设计
- **JavaScript**：交互逻辑
- **UI框架**：Bootstrap 5.3.0
- **图标**：Bootstrap Icons

## 项目结构

```
ESP32_cam_opencv/
├── app/                    # 应用主目录
│   ├── __init__.py         # 应用初始化
│   ├── routes/             # 路由模块
│   │   ├── __init__.py     # 路由初始化
│   │   └── main.py         # API端点实现
│   ├── models/             # 模型目录
│   │   └── __init__.py     # 模型初始化
│   ├── templates/          # HTML模板
│   │   └── index.html      # 主页面模板
│   └── static/             # 静态资源
│       ├── css/            # 样式文件
│       │   └── style.css   # 自定义样式
│       └── js/             # JavaScript文件
│           └── main.js     # 前端交互逻辑
├── config.py               # 应用配置
├── requirements.txt        # 依赖列表
├── run.py                  # 应用启动文件
└── README.md               # 项目文档
```

## 安装步骤

### 1. 克隆项目

```bash
git clone <repository-url>
cd ESP32_cam_opencv
```

### 2. 创建虚拟环境

```bash
# Windows
python -m venv .venv

# Linux/macOS
python3 -m venv .venv
```

### 3. 激活虚拟环境

```bash
# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate
```

### 4. 安装依赖

使用清华源安装依赖，提高下载速度和稳定性：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

### 5. 配置环境变量

创建 `.env` 文件，添加以下配置（根据实际情况修改）：

```env
# Flask配置
SECRET_KEY=your-secret-key
DEBUG=True

# Twilio配置
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_PHONE_NUMBER=your-twilio-phone-number
EMERGENCY_CONTACTS=+8613800138000,+8613900139000

# OpenAI API配置
OPENAI_API_KEY=your-openai-api-key
```

## 启动流程

### 1. 启动后端服务

```bash
# 方法1：直接运行
python run.py

# 方法2：使用虚拟环境中的Python解释器
.venv\Scripts\python.exe run.py
```

### 2. 访问Web界面

打开浏览器，访问以下地址：
- **Web界面**：http://127.0.0.1:5000
- **API文档**：http://127.0.0.1:5000

### 3. ESP32设备配置

将ESP32设备连接到与服务器相同的WiFi网络，配置设备发送图像到以下API端点：
- **目标检测**：http://<server-ip>:5000/api/detect

## API文档

### 1. 主页

- **URL**：`/`
- **方法**：`GET`
- **描述**：返回Web界面
- **响应**：HTML页面

### 2. 目标检测

- **URL**：`/api/detect`
- **方法**：`POST`
- **描述**：接收图像，进行目标检测，返回检测结果和语音播报文本
- **请求体**：`multipart/form-data`，包含`image`字段
- **响应**：
  ```json
  {
    "status": "success",
    "detections": [
      {
        "class": "person",
        "chinese_class": "行人",
        "confidence": 0.95,
        "bbox": [100, 200, 300, 400],
        "position": "正前方"
      }
    ],
    "announcement": "正前方检测到行人",
    "count": 1
  }
  ```

### 3. 位置查询

- **URL**：`/api/location`
- **方法**：`GET`
- **描述**：获取当前位置信息
- **响应**：
  ```json
  {
    "status": "success",
    "location": {
      "country": "中国",
      "region": "北京市",
      "city": "北京市",
      "zip": "100000",
      "lat": 39.9042,
      "lon": 116.4074,
      "isp": "中国电信",
      "ip": "123.123.123.123"
    },
    "announcement": "您当前在北京市附近"
  }
  ```

### 4. 紧急求助

- **URL**：`/api/emergency`
- **方法**：`POST`
- **描述**：发送求助信息给紧急联系人
- **响应**：
  ```json
  {
    "status": "success",
    "message": "求助信息已发送",
    "sent_count": 2,
    "location": {
      "city": "北京市"
    }
  }
  ```

### 5. 智能问答

- **URL**：`/api/ask`
- **方法**：`POST`
- **描述**：接收文本问题，返回AI回答
- **请求体**：
  ```json
  {
    "question": "附近有超市吗？"
  }
  ```
- **响应**：
  ```json
  {
    "status": "success",
    "answer": "根据您当前的位置，附近100米内有一家超市，位于您的正前方。",
    "question": "附近有超市吗？",
    "location": "北京市"
  }
  ```

## 使用说明

### Web界面使用

1. **目标检测**：
   - 点击"目标检测"标签
   - 点击"选择图像文件"按钮，选择一张图像
   - 点击"开始检测"按钮
   - 查看检测结果和语音播报文本

2. **位置查询**：
   - 点击"位置查询"标签
   - 点击"获取位置"按钮
   - 查看当前位置信息和语音播报文本

3. **紧急求助**：
   - 点击"紧急求助"标签
   - 点击"紧急求助"按钮
   - 在确认对话框中点击"确定"
   - 查看求助信息发送结果

4. **智能问答**：
   - 点击"智能问答"标签
   - 在文本框中输入问题
   - 点击"发送问题"按钮
   - 查看AI回答

### ESP32设备使用

1. 确保ESP32设备已连接到WiFi网络
2. 配置ESP32设备发送图像到服务器的`/api/detect`端点
3. 配置ESP32设备接收服务器返回的语音播报文本
4. 配置ESP32设备的一键求助按钮，发送请求到`/api/emergency`端点
5. 配置ESP32设备的语音输入功能，发送请求到`/api/ask`端点

## 注意事项

1. **YOLOv8模型**：首次运行时会自动下载YOLOv8模型（约6MB），请确保网络连接正常
2. **API密钥**：在生产环境中，务必保护好Twilio和OpenAI的API密钥，避免泄露
3. **性能优化**：对于资源有限的设备，可以使用更小的YOLOv8模型（如yolov8n.pt）
4. **生产部署**：在生产环境中，建议使用Gunicorn或uWSGI等WSGI服务器，配置HTTPS
5. **请求限制**：ip-api.com有请求限制，生产环境中应考虑使用付费服务或其他替代方案

## 许可证

本项目采用MIT许可证，详见LICENSE文件。

## 贡献

欢迎对本项目进行贡献！如果您有任何建议或问题，请提交Issue或Pull Request。

## 联系方式

如有任何问题或建议，请联系项目维护者：
- 邮箱：your-email@example.com
- GitHub：https://github.com/your-username/esp32-cam-opencv

---

**版本**：1.0.0
**最后更新**：2025-11-27
