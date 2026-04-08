#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json

# 测试AI智能问答API
def test_ask_api():
    url = "http://localhost:5000/api/ask"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "question": "你好，今天天气怎么样？"
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
    except Exception as e:
        print(f"请求失败: {str(e)}")

if __name__ == "__main__":
    test_ask_api()
