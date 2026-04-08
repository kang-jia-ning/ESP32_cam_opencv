#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
from config import Config

def test_doubao_api():
    """测试豆包API连接"""
    print("=== 豆包API测试 ===")
    
    # 检查配置
    print(f"API URL: {Config.DOUBAO_API_URL}")
    print(f"API Key: {Config.DOUBAO_API_KEY[:10]}...{Config.DOUBAO_API_KEY[-10:]}")
    print(f"Model: {Config.DOUBAO_MODEL}")
    
    # 构建请求
    url = Config.DOUBAO_API_URL
    headers = {
        "Authorization": f"Bearer {Config.DOUBAO_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": Config.DOUBAO_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "你是一个为视障人士提供帮助的智能助手，回答要简洁明了，适合语音播报。"
            },
            {
                "role": "user",
                "content": [
                    {
                        "text": "你好，请简单介绍一下你自己",
                        "type": "text"
                    }
                ]
            }
        ],
        "temperature": 0.7,
        "max_completion_tokens": 65535,
        "reasoning_effort": "medium"
    }
    
    try:
        print("\n正在发送请求到豆包API...")
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        print(f"HTTP状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API调用成功！")
            print(f"回答内容: {data['choices'][0]['message']['content']}")
            return True
        else:
            print("❌ API调用失败！")
            print(f"错误信息: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ 请求超时")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ 连接错误，请检查网络连接")
        return False
    except Exception as e:
        print(f"❌ 发生错误: {str(e)}")
        return False

def test_flask_api():
    """测试Flask应用的智能问答API"""
    print("\n=== Flask API测试 ===")
    
    url = "http://localhost:5000/api/ask"
    payload = {
        "question": "你好，请简单介绍一下你自己"
    }
    
    try:
        print("正在发送请求到Flask API...")
        response = requests.post(url, json=payload, timeout=10)
        
        print(f"HTTP状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"API状态: {data['status']}")
            if data['status'] == 'success':
                print("✅ Flask API调用成功！")
                print(f"回答内容: {data['answer']}")
                return True
            else:
                print(f"❌ Flask API返回错误: {data.get('message', '未知错误')}")
                return False
        else:
            print("❌ Flask API调用失败！")
            print(f"错误信息: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 发生错误: {str(e)}")
        return False

if __name__ == "__main__":
    print("开始测试豆包API配置...")
    
    # 测试直接调用豆包API
    api_success = test_doubao_api()
    
    # 测试Flask API
    flask_success = test_flask_api()
    
    print("\n=== 测试结果汇总 ===")
    print(f"豆包API连接: {'✅ 成功' if api_success else '❌ 失败'}")
    print(f"Flask API连接: {'✅ 成功' if flask_success else '❌ 失败'}")
    
    if api_success and flask_success:
        print("🎉 所有测试通过！豆包API已正确配置并可在网页中使用。")
    else:
        print("⚠️ 部分测试失败，请检查配置。")