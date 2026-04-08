#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json

def test_simple_ask():
    """测试简单的智能问答功能"""
    print("=== 简单智能问答测试 ===")
    
    # 测试数据
    test_data = {
        "question": "你好，请简单介绍一下你自己",
        "image_url": None  # 不使用图片
    }
    
    try:
        # 发送请求到Flask API
        response = requests.post(
            "http://127.0.0.1:5000/api/ask",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"HTTP状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Flask API调用成功！")
            print(f"回答: {result.get('answer', '无回答')}")
            print(f"状态: {result.get('status', '未知')}")
            return True
        else:
            print("❌ Flask API调用失败！")
            print(f"错误信息: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求异常: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他异常: {e}")
        return False

if __name__ == "__main__":
    print("开始测试智能问答功能...")
    success = test_simple_ask()
    
    if success:
        print("\n✅ 智能问答功能测试成功！")
        print("豆包API已正确配置并可以在网页中使用。")
    else:
        print("\n❌ 智能问答功能测试失败！")
        print("请检查网络连接和API配置。")