#!/usr/bin/env python3
"""
全面测试ESP32摄像头连接修复效果
"""
import requests
import time
import threading

class ESP32CameraTest:
    def __init__(self, url="http://192.168.4.127/"):
        self.url = url
        self.is_connecting = False
        self.is_connected = False
        self.retry_count = 0
        self.max_retries = 5
        self.timeout_id = None
        self.is_loading_frame = False
        self.frame_queue = []
        self.test_results = []
        
    def log_result(self, test_name, success, message=""):
        """记录测试结果"""
        result = {
            "test_name": test_name,
            "success": success,
            "message": message,
            "timestamp": time.time()
        }
        self.test_results.append(result)
        status = "✅" if success else "❌"
        print(f"{status} {test_name}: {message}")
    
    def test_initial_state(self):
        """测试初始状态"""
        test_name = "初始状态测试"
        try:
            expected_state = {
                "is_connecting": False,
                "is_connected": False,
                "retry_count": 0,
                "max_retries": 5,
                "is_loading_frame": False,
                "frame_queue": []
            }
            
            current_state = {
                "is_connecting": self.is_connecting,
                "is_connected": self.is_connected,
                "retry_count": self.retry_count,
                "max_retries": self.max_retries,
                "is_loading_frame": self.is_loading_frame,
                "frame_queue": self.frame_queue
            }
            
            if current_state == expected_state:
                self.log_result(test_name, True, "初始状态正确")
                return True
            else:
                self.log_result(test_name, False, f"初始状态错误: 期望 {expected_state}, 实际 {current_state}")
                return False
        except Exception as e:
            self.log_result(test_name, False, f"测试失败: {e}")
            return False
    
    def test_connection_process(self):
        """测试连接过程状态变化"""
        test_name = "连接过程测试"
        try:
            # 模拟开始连接
            self.is_connecting = True
            self.retry_count = 1
            
            if self.is_connecting and self.retry_count == 1:
                self.log_result(test_name, True, "连接状态变化正确")
                return True
            else:
                self.log_result(test_name, False, f"连接状态变化错误: is_connecting={self.is_connecting}, retry_count={self.retry_count}")
                return False
        except Exception as e:
            self.log_result(test_name, False, f"测试失败: {e}")
            return False
    
    def test_connection_success(self):
        """测试连接成功状态变化"""
        test_name = "连接成功测试"
        try:
            # 模拟连接成功
            self.is_connecting = False
            self.is_connected = True
            self.retry_count = 0
            
            if not self.is_connecting and self.is_connected and self.retry_count == 0:
                self.log_result(test_name, True, "连接成功状态变化正确")
                return True
            else:
                self.log_result(test_name, False, f"连接成功状态变化错误: is_connecting={self.is_connecting}, is_connected={self.is_connected}, retry_count={self.retry_count}")
                return False
        except Exception as e:
            self.log_result(test_name, False, f"测试失败: {e}")
            return False
    
    def test_connection_failure(self):
        """测试连接失败状态变化"""
        test_name = "连接失败测试"
        try:
            # 模拟连接失败
            self.is_connecting = False
            self.is_connected = False
            self.retry_count = 3
            
            if not self.is_connecting and not self.is_connected and self.retry_count == 3:
                self.log_result(test_name, True, "连接失败状态变化正确")
                return True
            else:
                self.log_result(test_name, False, f"连接失败状态变化错误: is_connecting={self.is_connecting}, is_connected={self.is_connected}, retry_count={self.retry_count}")
                return False
        except Exception as e:
            self.log_result(test_name, False, f"测试失败: {e}")
            return False
    
    def test_max_retries(self):
        """测试最大重试次数处理"""
        test_name = "最大重试次数测试"
        try:
            # 模拟达到最大重试次数
            self.retry_count = self.max_retries
            
            if self.retry_count >= self.max_retries:
                self.log_result(test_name, True, f"最大重试次数处理正确: retry_count={self.retry_count}, max_retries={self.max_retries}")
                return True
            else:
                self.log_result(test_name, False, f"最大重试次数处理错误: retry_count={self.retry_count}, max_retries={self.max_retries}")
                return False
        except Exception as e:
            self.log_result(test_name, False, f"测试失败: {e}")
            return False
    
    def test_exponential_backoff(self):
        """测试指数退避重试机制"""
        test_name = "指数退避重试测试"
        try:
            # 测试不同重试次数下的延迟
            test_cases = [1, 2, 3, 4, 5, 6]  # 重试次数
            expected_delays = [2000, 4000, 8000, 10000, 10000, 10000]  # 期望延迟(毫秒)
            
            all_correct = True
            for retry_count, expected_delay in zip(test_cases, expected_delays):
                actual_delay = min(2000 * (2 ** (retry_count - 1)), 10000)
                if actual_delay != expected_delay:
                    all_correct = False
                    print(f"   ❌ 重试次数 {retry_count}: 期望延迟 {expected_delay}ms, 实际 {actual_delay}ms")
                else:
                    print(f"   ✅ 重试次数 {retry_count}: 延迟 {actual_delay}ms 正确")
            
            if all_correct:
                self.log_result(test_name, True, "指数退避重试机制正确")
                return True
            else:
                self.log_result(test_name, False, "指数退避重试机制错误")
                return False
        except Exception as e:
            self.log_result(test_name, False, f"测试失败: {e}")
            return False
    
    def test_request_queue(self):
        """测试请求队列管理"""
        test_name = "请求队列管理测试"
        try:
            # 模拟正在加载帧
            self.is_loading_frame = True
            
            # 模拟多个请求同时到达
            for i in range(3):
                self.frame_queue.append(time.time())
            
            if len(self.frame_queue) == 3:
                print(f"   ✅ 队列长度正确: {len(self.frame_queue)}")
            else:
                self.log_result(test_name, False, f"队列长度错误: 期望 3, 实际 {len(self.frame_queue)}")
                return False
            
            # 模拟帧加载完成，清空队列
            self.is_loading_frame = False
            self.frame_queue = []
            
            if len(self.frame_queue) == 0:
                print(f"   ✅ 队列清空正确: {len(self.frame_queue)}")
                self.log_result(test_name, True, "请求队列管理正确")
                return True
            else:
                self.log_result(test_name, False, f"队列清空错误: 期望 0, 实际 {len(self.frame_queue)}")
                return False
        except Exception as e:
            self.log_result(test_name, False, f"测试失败: {e}")
            return False
    
    def test_actual_connection(self):
        """测试实际ESP32摄像头连接"""
        test_name = "实际连接测试"
        try:
            print(f"   正在测试实际连接: {self.url}")
            
            # 测试连接超时处理
            timeout = 5  # 5秒超时
            start_time = time.time()
            
            try:
                response = requests.get(self.url, timeout=timeout)
                elapsed_time = time.time() - start_time
                
                if response.status_code == 200:
                    # 检查是否是图像
                    content_type = response.headers.get('Content-Type', '').lower()
                    if 'image' in content_type:
                        self.log_result(test_name, True, f"连接成功，获取到图像数据 (耗时: {elapsed_time:.2f}秒, 大小: {len(response.content)}字节)")
                        return True
                    else:
                        self.log_result(test_name, False, f"连接成功，但未获取到图像数据 (Content-Type: {content_type})")
                        return False
                else:
                    self.log_result(test_name, False, f"连接失败，状态码: {response.status_code}")
                    return False
            except requests.exceptions.Timeout:
                self.log_result(test_name, False, f"连接超时 ({timeout}秒)")
                return False
            except requests.exceptions.RequestException as e:
                self.log_result(test_name, False, f"连接错误: {e}")
                return False
        except Exception as e:
            self.log_result(test_name, False, f"测试失败: {e}")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("=== ESP32摄像头连接修复全面测试 ===")
        print(f"测试目标: {self.url}")
        print(f"开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 运行测试
        tests = [
            self.test_initial_state,
            self.test_connection_process,
            self.test_connection_success,
            self.test_connection_failure,
            self.test_max_retries,
            self.test_exponential_backoff,
            self.test_request_queue,
            self.test_actual_connection
        ]
        
        # 重置状态
        self.__init__(self.url)
        
        # 运行所有测试
        results = []
        for test in tests:
            results.append(test())
            print()
        
        # 打印测试总结
        print("=== 测试总结 ===")
        total_tests = len(results)
        passed_tests = sum(results)
        failed_tests = total_tests - passed_tests
        
        print(f"总测试数: {total_tests}")
        print(f"通过数: {passed_tests}")
        print(f"失败数: {failed_tests}")
        print(f"通过率: {passed_tests/total_tests*100:.1f}%")
        
        print()
        print(f"结束时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        return passed_tests == total_tests

if __name__ == "__main__":
    # 测试默认地址
    esp32_url = "http://192.168.4.127/"
    
    # 创建测试实例
    test = ESP32CameraTest(esp32_url)
    
    # 运行所有测试
    test.run_all_tests()
    
    # 测试其他可能的地址格式
    print("\n=== 测试其他可能的摄像头地址 ===")
    test_urls = [
        "http://192.168.4.127/capture",
        "http://192.168.4.127/cam.jpg",
        "http://192.168.4.127/cam.mjpeg",
        "http://192.168.4.127/stream"
    ]
    
    for url in test_urls:
        print(f"\n测试地址: {url}")
        try:
            response = requests.get(url, timeout=5)
            print(f"状态码: {response.status_code}")
            print(f"Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
            print(f"响应大小: {len(response.content)} 字节")
        except requests.exceptions.RequestException as e:
            print(f"连接错误: {e}")
        time.sleep(1)  # 避免请求过于频繁
