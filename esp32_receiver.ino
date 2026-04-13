#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>
#include <Preferences.h>

#define PWDN_GPIO_NUM -1
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 5
#define Y9_GPIO_NUM 4
#define Y8_GPIO_NUM 6
#define Y7_GPIO_NUM 7
#define Y6_GPIO_NUM 14
#define Y5_GPIO_NUM 17
#define Y4_GPIO_NUM 21
#define Y3_GPIO_NUM 18
#define Y2_GPIO_NUM 16
#define VSYNC_GPIO_NUM 1
#define HREF_GPIO_NUM 2
#define PCLK_GPIO_NUM 15
#define SIOD_GPIO_NUM 8
#define SIOC_GPIO_NUM 9

#define LED_GPIO_NUM 47

// Preferences preferences;
const char *ssid;
const char *password;

// 创建WebServer实例（端口80）
WebServer server(80);

void startCameraServer();
void setupLedFlash(int pin);

void connectToWiFi(const char *ssid, const char *password)
{
    WiFi.begin(ssid, password);
    Serial.printf("Connecting to WiFi: %s\n", ssid);
    int retries = 0;
    while (WiFi.status() != WL_CONNECTED && retries < 20)
    {
        delay(500);
        Serial.print(".");
        retries++;
    }

    if (WiFi.status() == WL_CONNECTED)
    {
        Serial.println("\nWiFi connected!");
        Serial.print("IP address: ");
        Serial.println(WiFi.localIP());
    }
    else
    {
        Serial.println("\nFailed to connect to WiFi.");
    }
}

// void initWiFi() {
//   preferences.begin("wifi", false);
//   String savedSSID = "preferences.getString("ssid", "");"
//   String savedPASS = preferences.getString("password", "");
//   Serial.println("savedSSID");
//   Serial.println(savedSSID);

//   if (savedSSID.length() > 0 && savedPASS.length() > 0) {
//     Serial.println("Found saved WiFi credentials.");
//     connectToWiFi(savedSSID.c_str(), savedPASS.c_str());

//     if (WiFi.status() == WL_CONNECTED) {
//       return;
//     } else {
//       Serial.println("Stored credentials failed. Please enter new credentials.");
//     }
//   } else {
//     Serial.println("No WiFi credentials found. Please enter:");
//   }

//   while (Serial.available()) Serial.read();

//   Serial.println("Enter SSID: ");
//   while (Serial.available() == 0) delay(10);
//   String inputSSID = Serial.readStringUntil('\n');
//   inputSSID.trim();

//   Serial.println("Enter Password: ");
//   while (Serial.available() == 0) delay(10);
//   String inputPASS = Serial.readStringUntil('\n');
//   inputPASS.trim();

//   connectToWiFi(inputSSID.c_str(), inputPASS.c_str());

//   if (WiFi.status() == WL_CONNECTED) {
//     preferences.putString("ssid", inputSSID);
//     preferences.putString("password", inputPASS);
//     Serial.println("WiFi credentials saved.");
//   } else {
//     Serial.println("Failed to connect. Credentials not saved.");
//   }

//   preferences.end();
// }
void initWiFi()
{
    // 固定的 WiFi 凭证（请修改为你的网络信息）
    const char *FIXED_SSID = "HiwonderESP";
    const char *FIXED_PASSWORD = "hiwonder";

    Serial.println("Connecting to fixed WiFi...");
    Serial.print("SSID: ");
    Serial.println(FIXED_SSID);

    // 直接连接 WiFi
    connectToWiFi(FIXED_SSID, FIXED_PASSWORD);

    // 检查连接状态
    if (WiFi.status() == WL_CONNECTED)
    {
        Serial.println("WiFi connected successfully!");
        Serial.print("IP address: ");
        Serial.println(WiFi.localIP());
    }
    else
    {
        Serial.println("Failed to connect to WiFi!");
    }
}
void initCamera()
{
    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = Y2_GPIO_NUM;
    config.pin_d1 = Y3_GPIO_NUM;
    config.pin_d2 = Y4_GPIO_NUM;
    config.pin_d3 = Y5_GPIO_NUM;
    config.pin_d4 = Y6_GPIO_NUM;
    config.pin_d5 = Y7_GPIO_NUM;
    config.pin_d6 = Y8_GPIO_NUM;
    config.pin_d7 = Y9_GPIO_NUM;
    config.pin_xclk = XCLK_GPIO_NUM;
    config.pin_pclk = PCLK_GPIO_NUM;
    config.pin_vsync = VSYNC_GPIO_NUM;
    config.pin_href = HREF_GPIO_NUM;
    config.pin_sccb_sda = SIOD_GPIO_NUM;
    config.pin_sccb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;
    config.xclk_freq_hz = 20000000;
    config.frame_size = FRAMESIZE_UXGA;
    config.pixel_format = PIXFORMAT_JPEG; // for streaming
    // config.pixel_format = PIXFORMAT_RGB565; // for face detection/recognition
    config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
    config.fb_location = CAMERA_FB_IN_PSRAM;
    config.jpeg_quality = 12;
    config.fb_count = 1;

    // if PSRAM IC present, init with UXGA resolution and higher JPEG quality
    //                      for larger pre-allocated frame buffer.
    if (config.pixel_format == PIXFORMAT_JPEG)
    {
        if (psramFound())
        {
            config.jpeg_quality = 10;
            config.fb_count = 2;
            config.grab_mode = CAMERA_GRAB_LATEST;
        }
        else
        {
            // Limit the frame size when PSRAM is not available
            config.frame_size = FRAMESIZE_SVGA;
            config.fb_location = CAMERA_FB_IN_DRAM;
        }
    }
    else
    {
        // Best option for face detection/recognition
        config.frame_size = FRAMESIZE_240X240;
    }

    // camera init
    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK)
    {
        Serial.printf("Camera init failed with error 0x%x", err);
        return;
    }

    sensor_t *s = esp_camera_sensor_get();
    // initial sensors are flipped vertically and colors are a bit saturated
    if (s->id.PID == OV3660_PID)
    {
        s->set_vflip(s, 1);       // flip it back
        s->set_brightness(s, 1);  // up the brightness just a bit
        s->set_saturation(s, -2); // lower the saturation
    }
    // drop down frame size for higher initial frame rate
    if (config.pixel_format == PIXFORMAT_JPEG)
    {
        s->set_framesize(s, FRAMESIZE_QVGA);
    }
}

// 初始化HTTP服务器用于接收上位机发送的文本
void initHttpServer()
{
    // 设置接收检测结果的端点
    server.on("/api/announce", HTTP_POST, handleAnnouncement);

    // 备用端点（兼容不同命名）
    server.on("/announce", HTTP_POST, handleAnnouncement);
    server.on("/text", HTTP_POST, handleAnnouncement);
    server.on("/api/text", HTTP_POST, handleAnnouncement);
    server.on("/display", HTTP_POST, handleAnnouncement);

    // 启动服务器
    server.begin();
    Serial.println("HTTP服务器已启动");
    Serial.println("可用的API端点:");
    Serial.println("  POST /api/announce - 接收检测结果");
    Serial.println("  POST /announce - 接收检测结果");
    Serial.println("  POST /text - 接收文本");
}

// 处理接收到的检测结果
void handleAnnouncement()
{
    Serial.println("\n========== 收到上位机数据 ==========");

    // 检查是否有请求体
    if (!server.hasArg("plain"))
    {
        Serial.println("错误：没有接收到数据");
        server.send(400, "application/json", "{\"status\":\"error\",\"message\":\"No data received\"}");
        return;
    }

    // 获取请求体内容
    String body = server.arg("plain");

    // 在串口打印原始数据
    Serial.print("原始JSON数据: ");
    Serial.println(body);

    // 尝试解析JSON并提取text字段
    // 简单的字符串解析（不依赖ArduinoJson库）
    int textStart = body.indexOf("\"text\"");
    String textContent = "";

    if (textStart != -1)
    {
        // 找到 "text": " 后面的内容
        int colonPos = body.indexOf(':', textStart);
        if (colonPos != -1)
        {
            int quoteStart = body.indexOf('"', colonPos + 1);
            if (quoteStart != -1)
            {
                int quoteEnd = body.indexOf('"', quoteStart + 1);
                if (quoteEnd != -1)
                {
                    textContent = body.substring(quoteStart + 1, quoteEnd);
                }
            }
        }
    }

    // 打印提取的文本内容
    if (textContent.length() > 0)
    {
        Serial.print("提取的文本内容: ");
        Serial.println(textContent);

        // 可以在这里添加其他处理逻辑，例如：
        // - 显示到OLED屏幕
        // - 触发蜂鸣器
        // - 发送到串口2给其他设备
    }
    else
    {
        Serial.println("未能从JSON中提取text字段，请检查数据格式");
    }

    Serial.println("======================================\n");

    // 返回成功响应给上位机
    String response = "{\"status\":\"success\",\"message\":\"Text received successfully\",\"received_text\":\"" + textContent + "\"}";
    server.send(200, "application/json", response);
}

void setup()
{
    Serial.begin(115200);
    Serial.setDebugOutput(true);
    delay(1000);
    Serial.println("hello");

    initCamera();
    setupLedFlash(LED_GPIO_NUM);
    initWiFi();
    startCameraServer();

    // 初始化HTTP服务器用于接收上位机数据
    initHttpServer();

    Serial.println("\n系统初始化完成！");
    Serial.println("等待上位机连接和发送数据...");
    Serial.println("请在上位机输入此ESP32的IP地址");
}

void loop()
{
    // 处理HTTP请求（必须持续调用）
    server.handleClient();

    delay(10); // 短暂延迟，避免占用过多CPU
}
