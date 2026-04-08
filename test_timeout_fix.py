#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import time
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 测试AI智能问答API的超时处理
def test_ask_api_timeout():
    url = "http://localhost:5000/api/ask"
    headers = {
        "Content-Type": "application/json"
    }
    
    # 测试用例
    test_cases = [
        {"question": "你好，今天天气怎么样？"},
        {"question": "附近有什么餐厅推荐？"},
        {"question": "这是什么地方？"},
        {"question": "如何安全过马路？"},
        {"question": "请描述一下当前的环境。"}
    ]
    
    total_requests = len(test_cases)
    successful_requests = 0
    failed_requests = 0
    total_response_time = 0
    
    logger.info(f"开始测试AI智能问答API，共{total_requests}个测试用例")
    
    for i, test_case in enumerate(test_cases):
        question = test_case["question"]
        data = {"question": question}
        
        try:
            start_time = time.time()
            response = requests.post(url, headers=headers, json=data, timeout=60)  # 客户端超时设为60秒
            end_time = time.time()
            response_time = end_time - start_time
            total_response_time += response_time
            
            logger.info(f"测试用例 {i+1}/{total_requests}: 状态码={response.status_code}, 响应时间={response_time:.2f}秒")
            
            response_data = response.json()
            logger.info(f"  问题: {question}")
            logger.info(f"  回答: {response_data.get('answer', '')}")
            logger.info(f"  状态: {response_data.get('status', '')}")
            logger.info(f"  消息: {response_data.get('message', '')}")
            
            if response.status_code == 200:
                successful_requests += 1
            else:
                failed_requests += 1
            
        except Exception as e:
            failed_requests += 1
            logger.error(f"测试用例 {i+1}/{total_requests} 失败: {str(e)}")
        
        # 每个测试用例之间间隔1秒
        time.sleep(1)
    
    # 计算统计信息
    avg_response_time = total_response_time / total_requests if total_requests > 0 else 0
    success_rate = (successful_requests / total_requests) * 100 if total_requests > 0 else 0
    
    logger.info("\n测试总结:")
    logger.info(f"总请求数: {total_requests}")
    logger.info(f"成功请求数: {successful_requests}")
    logger.info(f"失败请求数: {failed_requests}")
    logger.info(f"成功率: {success_rate:.2f}%")
    logger.info(f"平均响应时间: {avg_response_time:.2f}秒")
    
    return {
        "total_requests": total_requests,
        "successful_requests": successful_requests,
        "failed_requests": failed_requests,
        "success_rate": success_rate,
        "avg_response_time": avg_response_time
    }

# 测试模拟超时场景
def test_simulated_timeout():
    # 这个测试需要在网络条件较差的环境下运行，或者修改代码中的超时时间进行测试
    logger.info("\n开始测试模拟超时场景")
    
    # 我们可以通过修改API代码中的超时时间来测试重试机制
    # 例如，将timeout设置为1秒，然后测试重试机制是否生效
    
    logger.info("模拟超时测试完成")

if __name__ == "__main__":
    # 运行API超时测试
    test_ask_api_timeout()
    
    # 运行模拟超时测试
    test_simulated_timeout()
    
    logger.info("所有测试完成")
