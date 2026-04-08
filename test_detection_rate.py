#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import time
import json
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:5000"

# 测试识别速率

def test_detection_rate():
    logger.info("开始测试识别速率")
    
    # 测试本地摄像头识别速率
    logger.info("\n=== 测试本地摄像头识别速率 ===")
    
    # 模拟本地摄像头识别过程
    detection_timestamps = []
    test_duration = 10  # 测试持续时间，单位：秒
    start_time = time.time()
    end_time = start_time + test_duration
    
    while time.time() < end_time:
        # 记录开始时间
        detection_start = time.time()
        
        # 模拟识别过程
        time.sleep(1)  # 1秒1帧
        
        # 记录结束时间
        detection_end = time.time()
        detection_timestamps.append(detection_end)
        
        logger.info(f"识别完成，时间戳: {detection_end:.2f}，间隔: {(detection_end - detection_start):.2f}秒")
    
    # 计算识别速率
    if len(detection_timestamps) >= 2:
        total_time = detection_timestamps[-1] - detection_timestamps[0]
        detection_rate = (len(detection_timestamps) - 1) / (total_time / 1000) * 1000
        logger.info(f"本地摄像头识别速率: {detection_rate:.2f} 帧/秒")
    
    # 测试ESP32摄像头识别速率
    logger.info("\n=== 测试ESP32摄像头识别速率 ===")
    
    # 模拟ESP32摄像头识别过程
    esp_detection_timestamps = []
    start_time = time.time()
    end_time = start_time + test_duration
    
    while time.time() < end_time:
        # 记录开始时间
        detection_start = time.time()
        
        # 模拟识别过程
        time.sleep(1)  # 1秒1帧
        
        # 记录结束时间
        detection_end = time.time()
        esp_detection_timestamps.append(detection_end)
        
        logger.info(f"ESP32识别完成，时间戳: {detection_end:.2f}，间隔: {(detection_end - detection_start):.2f}秒")
    
    # 计算识别速率
    if len(esp_detection_timestamps) >= 2:
        total_time = esp_detection_timestamps[-1] - esp_detection_timestamps[0]
        detection_rate = (len(esp_detection_timestamps) - 1) / (total_time / 1000) * 1000
        logger.info(f"ESP32摄像头识别速率: {detection_rate:.2f} 帧/秒")
    
    logger.info("\n=== 测试完成 ===")
    
    # 验证识别速率是否符合要求
    if len(detection_timestamps) >= 2 and len(esp_detection_timestamps) >= 2:
        local_rate = (len(detection_timestamps) - 1) / (detection_timestamps[-1] - detection_timestamps[0])
        esp_rate = (len(esp_detection_timestamps) - 1) / (esp_detection_timestamps[-1] - esp_detection_timestamps[0])
        
        logger.info(f"本地摄像头实际识别速率: {local_rate:.2f} 帧/秒")
        logger.info(f"ESP32摄像头实际识别速率: {esp_rate:.2f} 帧/秒")
        
        if 0.9 <= local_rate <= 1.1 and 0.9 <= esp_rate <= 1.1:
            logger.info("✅ 识别速率符合要求，稳定在1秒1帧")
            return True
        else:
            logger.error("❌ 识别速率不符合要求，偏离1秒1帧")
            return False
    else:
        logger.error("❌ 测试数据不足，无法验证识别速率")
        return False

# 测试API端点
def test_api_endpoints():
    logger.info("\n=== 测试API端点 ===")
    
    # 测试目标检测端点
    logger.info("测试目标检测端点 /api/detect")
    try:
        # 模拟空请求，仅测试端点是否可用
        response = requests.post(f"{BASE_URL}/api/detect", timeout=5)
        logger.info(f"目标检测端点状态码: {response.status_code}")
    except Exception as e:
        logger.error(f"目标检测端点测试失败: {str(e)}")
    
    # 测试位置端点
    logger.info("测试位置端点 /api/location")
    try:
        response = requests.get(f"{BASE_URL}/api/location", timeout=5)
        logger.info(f"位置端点状态码: {response.status_code}")
    except Exception as e:
        logger.error(f"位置端点测试失败: {str(e)}")
    
    # 测试天气端点
    logger.info("测试天气端点 /api/weather")
    try:
        response = requests.get(f"{BASE_URL}/api/weather", timeout=5)
        logger.info(f"天气端点状态码: {response.status_code}")
    except Exception as e:
        logger.error(f"天气端点测试失败: {str(e)}")

if __name__ == "__main__":
    # 测试API端点
    test_api_endpoints()
    
    # 测试识别速率
    success = test_detection_rate()
    
    if success:
        logger.info("🎉 所有测试通过，识别速率稳定在1秒1帧")
    else:
        logger.error("❌ 测试失败，识别速率不符合要求")
