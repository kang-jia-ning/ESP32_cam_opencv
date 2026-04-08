# 视障人士智能辅助工具

## 项目概述

视障人士智能辅助工具是一个基于AI技术的出行辅助系统，专为视障人士设计。该系统通过ESP32-S3硬件设备采集摄像头图像，传输到后端服务器进行实时处理和分析，然后将结果以语音播报的形式反馈给用户，帮助视障人士感知周围环境，提高出行安全性和独立性。

## 功能介绍

### 1. 实时目标检测
- **功能**：识别道路上的关键目标，如行人、车辆、自行车、交通标志等
- **技术**：基于YOLOv8深度学习模型
- **应用**：生成语音播报文本，如"正前方检测到行人"、"左前方检测到车辆"
- **支持目标**：行人(person)、车辆(car)、自行车(bicycle)、摩托车(motorcycle)、停止标志(stop sign)、交通灯(traffic light)、狗(dog)、猫(cat)

### 2. 位置服务 (IP定位/GPS定位)
- **功能**：获取设备当前地理位置
- **技术**：集成高德地图IP定位API和逆地理编码API
- **应用**：语音播报当前位置，如"您当前在北京市附近"
- **特性**：支持GPS经纬度精确定位和IP地址粗略定位

### 3. 天气查询
- **功能**：查询当前位置或指定城市的实时天气信息
- **技术**：集成高德地图天气API
- **应用**：语音播报天气状况，如"当前北京的天气状况是晴，温度25度，湿度60%"
- **特性**：支持经纬度、城市名称、自动IP定位三种查询方式

### 4. 紧急联系人呼叫
- **功能**：一键发送求助信息给预设紧急联系人
- **技术**：集成Twilio短信服务
- **应用**：发送包含位置信息的求助短信，如"紧急求助：我可能在北京市附近遇到麻烦，请尽快联系我。"

### 5. 智能问答
- **功能**：基于大语言模型的智能问答，结合位置上下文
- **技术**：
  - 豆包API（推荐）：火山引擎大语言模型
  - OpenAI API：GPT系列模型
  - 模拟回答模式（测试用）
- **应用**：回答用户问题，自动识别天气查询并整合天气数据
- **特性**：支持多模态输入（文本+图像）、自动重试机制、降级策略

## 技术栈

### 后端
- **框架**：Flask >= 2.3.0
- **AI模型**：YOLOv8 (ultralytics)
- **图像处理**：OpenCV >= 4.8.0
- **数值计算**：NumPy >= 1.24.0
- **HTTP请求**：Requests >= 2.31.0
- **短信服务**：Twilio >= 8.0.0
- **大语言模型**：豆包API / OpenAI API
- **地图服务**：高德地图API（IP定位、逆地理编码、天气查询）
- **环境配置**：python-dotenv >= 1.0.0
- **图像处理辅助**：Pillow >= 10.0.0

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
│   │   ├── main.py         # 主要API端点实现（目标检测、位置、天气、紧急求助、问答）
│   │   └── esp32.py        # ESP32设备相关路由
│   ├── models/             # 模型目录
│   │   └── __init__.py     # 模型初始化
│   ├── templates/          # HTML模板
│   │   └── index.html      # 主页面模板
│   └── static/             # 静态资源
│       ├── css/            # 样式文件
│       │   └── style.css   # 自定义样式
│       └── js/             # JavaScript文件
│           └── main.js     # 前端交互逻辑
├── config.py               # 应用配置（所有API密钥和环境变量）
├── requirements.txt        # Python依赖列表
├── run.py                  # 应用启动文件
├── .env                    # 环境变量配置文件（需自行创建）
└── README.md               # 项目文档
```

## 安装步骤

### 1. 克隆项目

```bash
git clone https://github.com/kang-jia-ning/ESP32_cam_opencv.git
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
SECRET_KEY=your-secret-key-change-in-production
DEBUG=True

# YOLOv8模型配置
YOLO_MODEL_PATH=yolov8n.pt
YOLO_CONF_THRESHOLD=0.5
YOLO_IOU_THRESHOLD=0.45

# Twilio配置（紧急求助功能）
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_PHONE_NUMBER=your-twilio-phone-number
EMERGENCY_CONTACTS=+8613800138000,+8613900139000

# 豆包API配置（推荐用于智能问答）
DOUBAO_API_KEY=your-doubao-api-key
DOUBAO_API_URL=https://ark.cn-beijing.volces.com/api/v3/chat/completions
DOUBAO_MODEL=doubao-seed-1-6-251015

# OpenAI API配置（备选方案）
OPENAI_API_KEY=your-openai-api-key

# 高德地图API配置（位置服务和天气查询）
AMAP_API_KEY=your-amap-api-key
```

## 启动流程

### 1. 启动后端服务

```bash
# 方法1：直接运行
python run.py

# 方法2：使用虚拟环境中的Python解释器
.venv\Scripts\python.exe run.py
```

服务将在 `http://0.0.0.0:5000` 启动。

### 2. 访问Web界面

打开浏览器，访问以下地址：
- **Web界面**：http://127.0.0.1:5000
- **目标检测API**：http://127.0.0.1:5000/api/detect
- **位置查询API**：http://127.0.0.1:5000/api/location
- **天气查询API**：http://127.0.0.1:5000/api/weather
- **紧急求助API**：http://127.0.0.1:5000/api/emergency
- **智能问答API**：http://127.0.0.1:5000/api/ask

### 3. ESP32设备配置

将ESP32设备连接到与服务器相同的WiFi网络，配置设备发送请求到以下API端点：
- **目标检测**：POST `http://<server-ip>:5000/api/detect` （multipart/form-data，包含image字段）
- **紧急求助**：POST `http://<server-ip>:5000/api/emergency`
- **智能问答**：POST `http://<server-ip>:5000/api/ask` （JSON格式，包含question字段）

## API文档

### 1. 主页

- **URL**：`GET /`
- **描述**：返回Web界面
- **响应**：HTML页面

---

### 2. 目标检测

- **URL**：`POST /api/detect`
- **描述**：接收图像，使用YOLOv8进行目标检测，返回检测结果和语音播报文本
- **Content-Type**：`multipart/form-data`
- **请求参数**：
  - `image`（必填）：图像文件
- **响应示例**：
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

---

### 3. 位置查询

- **URL**：`GET /api/location`
- **描述**：获取当前位置信息，支持IP定位和GPS定位两种方式
- **请求参数**：
  - `lat`（可选）：纬度，与lon配合使用进行GPS精确定位
  - `lon`（可选）：经度，与lat配合使用进行GPS精确定位
- **响应示例**（IP定位）：
  ```json
  {
    "status": "success",
    "location": {
      "country": "中国",
      "region": "北京市",
      "city": "北京市",
      "lat": 39.9042,
      "lon": 116.4074,
      "isp": "中国电信",
      "ip": "123.123.123.123"
    },
    "announcement": "您当前在北京市附近"
  }
  ```
- **响应示例**（GPS定位）：
  ```json
  {
    "status": "success",
    "location": {
      "country": "中国",
      "region": "北京市",
      "city": "北京市",
      "district": "朝阳区",
      "street": "建国路",
      "street_number": "88号",
      "lat": 39.9042,
      "lon": 116.4074,
      "address": "中国北京市朝阳区建国路88号",
      "ip": "123.123.123.123"
    },
    "announcement": "您当前在北京市附近"
  }
  ```

---

### 4. 天气查询

- **URL**：`GET /api/weather`
- **描述**：查询实时天气信息，支持多种查询方式
- **请求参数**（三选一）：
  - `lat` + `lon`：使用经纬度查询（会先通过逆地理编码获取城市名）
  - `city`：使用城市名称直接查询
  - 无参数：自动通过IP定位获取当前位置并查询天气
- **响应示例**：
  ```json
  {
    "status": "success",
    "weather": {
      "basic": {
        "city": "北京",
        "province": "北京",
        "update_time": "2025-11-27 10:00+08:00"
      },
      "now": {
        "weather": "晴",
        "temperature": "25",
        "humidity": "60",
        "wind_direction": "东北",
        "wind_power": "3",
        "pressure": "1015",
        "visibility": "10",
        "dew_point": "15"
      },
      "forecast": {}
    },
    "announcement": "当前北京的天气状况是晴，温度25度，湿度60%，东北风3级"
  }
  ```

---

### 5. 紧急求助

- **URL**：`POST /api/emergency`
- **描述**：发送求助信息给预设的紧急联系人
- **响应示例**：
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

---

### 6. 智能问答

- **URL**：`POST /api/ask`
- **描述**：接收文本问题，调用大语言模型API返回回答，自动整合位置上下文和天气信息
- **Content-Type**：`application/json` 或 `multipart/form-data`
- **请求参数**：
  - `question`（必填）：用户问题文本
  - `image`（可选）：图像文件（多模态支持）
- **请求体示例**：
  ```json
  {
    "question": "附近有超市吗？"
  }
  ```
- **响应示例**：
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
   - 点击"目标检测"标签页
   - 点击"选择图像文件"按钮，选择一张图像
   - 点击"开始检测"按钮
   - 查看检测结果列表和语音播报文本

2. **位置查询**：
   - 点击"位置查询"标签页
   - 点击"获取位置"按钮
   - 查看当前位置详细信息和语音播报文本

3. **天气查询**：
   - 点击"天气查询"标签页
   - 可选择输入城市名称或直接获取当前位置天气
   - 点击"查询天气"按钮
   - 查看实时天气信息和语音播报文本

4. **紧急求助**：
   - 点击"紧急求助"标签页
   - 点击"紧急求助"按钮
   - 在确认对话框中点击"确定"
   - 查看求助信息发送结果

5. **智能问答**：
   - 点击"智能问答"标签页
   - 在文本框中输入问题（如"今天天气怎么样？"、"附近有什么危险？"）
   - 点击"发送问题"按钮
   - 查看AI回答（系统会自动结合位置上下文）

### ESP32设备使用

1. 确保ESP32设备已连接到WiFi网络
2. 配置ESP32设备发送图像到服务器的 `/api/detect` 端点
3. 配置ESP32设备接收服务器返回的语音播报文本并进行TTS播报
4. 配置ESP32设备的一键求助按钮，发送POST请求到 `/api/emergency` 端点
5. 配置ESP32设备的语音输入功能，将识别的文本发送到 `/api/ask` 端点

## 注意事项

1. **YOLOv8模型**：首次运行时会自动下载YOLOv8模型（约6MB），请确保网络连接正常。可通过环境变量 `YOLO_MODEL_PATH` 切换不同大小的模型（yolov8n.pt / yolov8s.pt / yolov8m.pt / yolov8l.pt / yolov8x.pt）

2. **API密钥安全**：在生产环境中，务必保护好以下API密钥，避免泄露：
   - Twilio凭证（TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN）
   - 豆包API密钥（DOUBAO_API_KEY）
   - OpenAI API密钥（OPENAI_API_KEY）
   - 高德地图API密钥（AMAP_API_KEY）

3. **性能优化建议**：
   - 对于资源有限的设备，使用更小的YOLOv8模型（如yolov8n.pt）
   - 豆包API默认设置30秒超时，支持3次自动重试（指数退避）
   - 当LLM服务不可用时，系统会自动降级返回模拟回答

4. **生产部署**：
   - 建议使用Gunicorn或uWSGI等WSGI服务器
   - 配置HTTPS加密传输
   - 设置防火墙规则，限制API访问权限
   - 配置日志轮转和监控告警

5. **高德地图API限制**：
   - 免费版有日调用量限制（5000次/日）
   - IP定位精度受限于IP数据库
   - 生产环境中可考虑升级为企业版以获得更高配额

6. **Twilio注意事项**：
   - 需要购买Twilio电话号码才能发送短信
   - 国际短信可能需要额外配置
   - 请确保紧急联系人号码格式正确（含国际区号）

## 许可证

本项目采用MIT许可证，详见LICENSE文件。

## 贡献

欢迎对本项目进行贡献！如果您有任何建议或问题，请提交Issue或Pull Request。

## 联系方式

如有任何问题或建议，请联系项目维护者：
- GitHub：https://github.com/kang-jia-ning/ESP32_cam_opencv

---

**版本**：1.1.0
**最后更新**：2026-04-08
