#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:5000"

# 测试定位功能
def test_location():
    logger.info("\n=== 测试定位功能 ===")
    
    # 测试1: 基本定位请求
    logger.info("测试1: 基本定位请求")
    try:
        response = requests.get(f"{BASE_URL}/api/location", timeout=10)
        logger.info(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"响应内容: {json.dumps(data, ensure_ascii=False, indent=2)}")
            if data['status'] == 'success':
                logger.info("✅ 基本定位请求成功")
                return data['location']
            else:
                logger.error(f"❌ 基本定位请求失败: {data['message']}")
        else:
            logger.error(f"❌ 基本定位请求失败，状态码: {response.status_code}")
    except Exception as e:
        logger.error(f"❌ 基本定位请求异常: {str(e)}")
    
    return None

# 测试天气功能
def test_weather(location=None):
    logger.info("\n=== 测试天气功能 ===")
    
    # 测试1: 基于IP定位的天气查询
    logger.info("测试1: 基于IP定位的天气查询")
    try:
        response = requests.get(f"{BASE_URL}/api/weather", timeout=10)
        logger.info(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"响应内容: {json.dumps(data, ensure_ascii=False, indent=2)}")
            if data['status'] == 'success':
                logger.info("✅ 基于IP定位的天气查询成功")
        else:
            logger.error(f"❌ 基于IP定位的天气查询失败，状态码: {response.status_code}")
    except Exception as e:
        logger.error(f"❌ 基于IP定位的天气查询异常: {str(e)}")
    
    # 测试2: 基于城市名称的天气查询
    logger.info("测试2: 基于城市名称的天气查询")
    try:
        city = "北京"
        response = requests.get(f"{BASE_URL}/api/weather?city={city}", timeout=10)
        logger.info(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"响应内容: {json.dumps(data, ensure_ascii=False, indent=2)}")
            if data['status'] == 'success':
                logger.info("✅ 基于城市名称的天气查询成功")
        else:
            logger.error(f"❌ 基于城市名称的天气查询失败，状态码: {response.status_code}")
    except Exception as e:
        logger.error(f"❌ 基于城市名称的天气查询异常: {str(e)}")
    
    # 测试3: 基于经纬度的天气查询
    if location:
        logger.info("测试3: 基于经纬度的天气查询")
        try:
            lat = location['lat']
            lon = location['lon']
            response = requests.get(f"{BASE_URL}/api/weather?lat={lat}&lon={lon}", timeout=10)
            logger.info(f"状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"响应内容: {json.dumps(data, ensure_ascii=False, indent=2)}")
                if data['status'] == 'success':
                    logger.info("✅ 基于经纬度的天气查询成功")
            else:
                logger.error(f"❌ 基于经纬度的天气查询失败，状态码: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ 基于经纬度的天气查询异常: {str(e)}")

# 测试智能问答的天气查询
def test_ask_weather():
    logger.info("\n=== 测试智能问答的天气查询 ===")
    
    # 测试1: 询问天气
    logger.info("测试1: 询问天气")
    try:
        question = "今天天气怎么样？"
        response = requests.post(f"{BASE_URL}/api/ask", 
                                headers={"Content-Type": "application/json"}, 
                                json={"question": question}, 
                                timeout=10)
        logger.info(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"问题: {question}")
            logger.info(f"回答: {data['answer']}")
            logger.info(f"状态: {data['status']}")
            if data['status'] == 'success' or data['status'] == 'warning':
                logger.info("✅ 智能问答的天气查询成功")
        else:
            logger.error(f"❌ 智能问答的天气查询失败，状态码: {response.status_code}")
    except Exception as e:
        logger.error(f"❌ 智能问答的天气查询异常: {str(e)}")
    
    # 测试2: 询问温度
    logger.info("测试2: 询问温度")
    try:
        question = "今天多少度？"
        response = requests.post(f"{BASE_URL}/api/ask", 
                                headers={"Content-Type": "application/json"}, 
                                json={"question": question}, 
                                timeout=10)
        logger.info(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"问题: {question}")
            logger.info(f"回答: {data['answer']}")
            logger.info(f"状态: {data['status']}")
            if data['status'] == 'success' or data['status'] == 'warning':
                logger.info("✅ 智能问答的温度查询成功")
        else:
            logger.error(f"❌ 智能问答的温度查询失败，状态码: {response.status_code}")
    except Exception as e:
        logger.error(f"❌ 智能问答的温度查询异常: {str(e)}")

# 主测试函数
def main():
    logger.info("开始测试高德地图API集成")
    
    # 测试定位功能
    location = test_location()
    
    # 测试天气功能
    test_weather(location)
    
    # 测试智能问答的天气查询
    test_ask_weather()
    
    logger.info("\n=== 测试完成 ===")

if __name__ == "__main__":
    main()
