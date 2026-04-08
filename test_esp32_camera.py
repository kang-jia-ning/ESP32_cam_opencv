#!/usr/bin/env python3
"""
测试ESP32摄像头连接
"""
import requests
import time

def test_esp32_camera(url):
    """测试ESP32摄像头连接"""
    print(f"测试ESP32摄像头连接: {url}")
    
    try:
        # 尝试获取摄像头图像
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            print("✅ ESP32摄像头连接成功！")
            print(f"响应内容类型: {response.headers.get('Content-Type', 'Unknown')}")
            print(f"响应大小: {len(response.content)} 字节")
            
            # 检查是否是图像
            content_type = response.headers.get('Content-Type', '').lower()
            if 'image' in content_type:
                print("✅ 检测到图像数据")
            else:
                print("⚠️ 响应内容可能不是图像")
                
        else:
            print(f"❌ ESP32摄像头连接失败，状态码: {response.status_code}")
            print(f"响应内容: {response.text[:200]}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ ESP32摄像头连接错误: {e}")
        print("请检查:")
        print("1. ESP32设备是否已开机并连接到WiFi")
        print("2. 电脑是否连接到ESP32的WiFi网络")
        print("3. 摄像头地址是否正确")
        print("4. 网络连接是否正常")

if __name__ == "__main__":
    # 测试默认地址
    esp32_url = "http://192.168.4.127/"
    test_esp32_camera(esp32_url)
    
    # 测试可能的其他地址格式
    # test_urls = [
    #     "http://192.168.4.127/capture",
    #     "http://192.168.4.127/cam.jpg",
    #     "http://192.168.4.127/cam.mjpeg",
    #     "http://192.168.4.127/stream"
    # ]
    
    # print("\n测试其他可能的摄像头地址:")
    # for url in test_urls:
    #     print(f"\n测试地址: {url}")
    #     test_esp32_camera(url)
    #     time.sleep(1)  # 避免请求过于频繁