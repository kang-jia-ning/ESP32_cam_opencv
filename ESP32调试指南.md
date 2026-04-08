# ESP32摄像头调试指南

## 问题诊断与解决步骤

### 一、基础网络检查

#### 1. 确认ESP32 IP地址
您的ESP32摄像头IP地址：`192.168.241.121`

**验证方法：**
- 在浏览器中直接访问：`http://192.168.241.121/`
- 如果能看到ESP32的网页界面，说明基础网络连接正常

#### 2. Ping测试
**Windows系统：**
```cmd
ping -n 4 192.168.241.121
```

**Linux/Mac系统：**
```bash
ping -c 4 192.168.241.121
```

**预期结果：**
- 应该有响应，延迟在1-100ms之间
- 如果超时，说明网络连接有问题

#### 3. 确认在同一网络
- 检查您的电脑IP地址是否在同一网段（如192.168.241.x）
- 确保没有防火墙阻止连接

---

### 二、ESP32端点测试

根据您的 `app_httpd.cpp`，ESP32提供以下端点：

| 端点 | 端口 | 功能 | Content-Type |
|------|------|------|--------------|
| `/` | 80 | 主页 | text/html |
| `/status` | 80 | 摄像头状态 | application/json |
| `/control` | 80 | 控制参数 | - |
| `/capture` | 80 | 单张JPEG | image/jpeg |
| `/bmp` | 80 | 单张BMP | image/bmp |
| `/stream` | **81** | **MJPEG视频流** | **multipart/x-mixed-replace** |

#### 测试方法

**1. 测试主页（端口80）**
```
http://192.168.241.121/
```
- 应该能看到ESP32的HTML网页

**2. 测试单帧捕获（端口80）**
```
http://192.168.241.121/capture
```
- 应该能看到一张JPEG图片

**3. 测试MJPEG流（端口81）** ← 最关键！
```
http://192.168.241.121:81/stream
```
- 浏览器应该显示不断刷新的视频流
- 这是我们需要的视频流端点！

---

### 三、使用本项目的诊断功能

#### 方法1：前端直接连接

1. 打开 http://127.0.0.1:5000
2. 切换到"ESP32摄像头"
3. 输入地址：`http://192.168.241.121/`
4. 点击"ESP32摄像头"按钮
5. 系统会自动：
   - 测试端口80和81
   - 检测所有可用端点
   - 找到最佳视频流端点

#### 方法2：后端API诊断

您也可以直接调用后端诊断API：

```bash
curl -X POST http://127.0.0.1:5000/esp32/diagnose \
  -H "Content-Type: application/json" \
  -d '{"url": "http://192.168.241.121/"}'
```

---

### 四、常见问题排查

#### 问题1：完全无法连接到ESP32

**可能原因：**
- ESP32未开机
- 不在同一WiFi网络
- IP地址错误

**解决步骤：**
1. 确认ESP32电源指示灯亮
2. 查看ESP32串口输出，确认IP地址
3. 确认电脑和ESP32连接到同一WiFi
4. 尝试重新连接WiFi

#### 问题2：能访问主页，但看不到视频流

**可能原因：**
- 视频流服务器（端口81）未启动
- 防火墙阻止端口81

**解决步骤：**
1. 直接访问 `http://192.168.241.121:81/stream`
2. 如果无法访问，检查ESP32固件
3. 确认 `app_httpd.cpp` 中的流服务器已启用

#### 问题3：视频流断断续续

**可能原因：**
- WiFi信号弱
- ESP32处理能力不足
- 网络带宽不足

**解决步骤：**
1. 减少ESP32摄像头分辨率
2. 靠近WiFi路由器
3. 减少网络中其他设备的带宽占用

---

### 五、ESP32固件检查

确保您的 `app_httpd.cpp` 中包含以下关键代码：

```cpp
// 启动主服务器（默认端口）
if (httpd_start(&camera_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(camera_httpd, &index_uri);
    httpd_register_uri_handler(camera_httpd, &status_uri);
    httpd_register_uri_handler(camera_httpd, &control_uri);
    httpd_register_uri_handler(camera_httpd, &capture_uri);
}

// 启动流服务器（端口+1）
config.server_port += 1;
config.ctrl_port += 1;
if (httpd_start(&stream_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(stream_httpd, &stream_uri);
}
```

关键要点：
1. **双服务器架构**：主服务器在默认端口，流服务器在端口+1
2. **流端点**：`/stream` 只在流服务器上注册
3. **MJPEG格式**：使用 `multipart/x-mixed-replace` 协议

---

### 六、快速测试清单

在使用本项目前，请确认：

- [ ] ESP32已开机并连接到WiFi
- [ ] 能ping通 `192.168.241.121`
- [ ] 能在浏览器访问 `http://192.168.241.121/`
- [ ] 能在浏览器访问 `http://192.168.241.121:81/stream`
- [ ] 电脑和ESP32在同一网络
- [ ] 防火墙允许相关端口

---

### 七、获取帮助

如果以上步骤都无法解决问题：

1. 查看浏览器控制台（F12）的错误信息
2. 查看Flask服务器的日志输出
3. 提供以下信息：
   - ESP32固件版本
   - 浏览器控制台错误
   - Flask服务器日志
   - 网络拓扑图

---

## 附录：ESP32端点完整列表

### 端口80（主服务器）
- `/` - 主页（HTML）
- `/status` - 摄像头状态（JSON）
- `/control` - 控制参数
- `/capture` - JPEG单帧捕获
- `/bmp` - BMP单帧捕获
- `/save` - 保存到SPIFFS
- `/saved.jpg` - 读取已保存的JPEG
- `/delete` - 删除已保存的图片
- `/ota` - OTA更新页面
- `/favicon.ico` - 网站图标

### 端口81（流服务器）
- `/stream` - MJPEG视频流 ← **关键！**

---

**最后更新**：2026-03-31