"""
ESP32摄像头代理路由
处理ESP32摄像头的视频流代理和协议转换
"""

import requests
from flask import Blueprint, Response, request, jsonify
import threading
import time
from io import BytesIO
import traceback
import subprocess
import platform

esp32_bp = Blueprint('esp32', __name__)

# 缓存配置
CACHE_SIZE = 10
frame_cache = {}
cache_lock = threading.Lock()

# 连接状态
connection_status = {}

class ESP32CameraProxy:
    """ESP32摄像头代理类"""
    
    def __init__(self, base_url):
        self.base_url = base_url
        self.running = False
        self.current_frame = None
        self.frame_thread = None
        self.last_error = None
        self.stats = {
            'frames_received': 0,
            'last_frame_time': None,
            'errors': 0,
            'fps': 0
        }
    
    def start(self):
        """启动代理"""
        if self.running:
            return
        
        self.running = True
        self.frame_thread = threading.Thread(target=self._fetch_frames, daemon=True)
        self.frame_thread.start()
    
    def stop(self):
        """停止代理"""
        self.running = False
        if self.frame_thread:
            self.frame_thread.join(timeout=2)
    
    def _fetch_frames(self):
        """获取帧循环"""
        last_time = time.time()
        frame_count = 0
        
        from urllib.parse import urlparse
        try:
            parsed = urlparse(self.base_url)
            host = parsed.hostname
            protocol = parsed.scheme
            port = parsed.port
            if not port:
                port = 443 if protocol == 'https' else 80
        except:
            host = self.base_url.split('/')[2] if '//' in self.base_url else self.base_url.split('/')[0]
            protocol = 'http'
            port = 80
        
        test_ports = [port, port + 1] if isinstance(port, int) else [port]
        endpoints = ['/stream', '/', '/video', '/camera', '/snapshot', '/image']
        
        best_url = None
        best_type = None
        
        for test_port in test_ports:
            port_str = f':{test_port}' if test_port not in [80, 443] else ''
            port_url = f'{protocol}://{host}{port_str}'
            
            for endpoint in endpoints:
                test_url = port_url + endpoint
                try:
                    response = requests.get(test_url, timeout=3)
                    if response.status_code == 200:
                        content_type = response.headers.get('Content-Type', '')
                        if 'multipart/x-mixed-replace' in content_type:
                            best_url = test_url
                            best_type = 'mjpeg'
                            break
                        elif 'image/' in content_type and not best_url:
                            best_url = test_url
                            best_type = 'image'
                except:
                    continue
            if best_type == 'mjpeg':
                break
        
        if not best_url:
            best_url = self.base_url.rstrip('/') + '/stream'
            best_type = 'unknown'
        
        print(f"使用视频流地址: {best_url} (类型: {best_type})")
        
        while self.running:
            try:
                if best_type == 'mjpeg':
                    try:
                        response = requests.get(best_url, timeout=5, stream=True)
                        if response.status_code == 200:
                            content_type = response.headers.get('Content-Type', '')
                            if 'multipart/x-mixed-replace' in content_type:
                                self._process_mjpeg_stream(response)
                                continue
                    except Exception as e:
                        pass
                
                frame = None
                for test_port in test_ports:
                    port_str = f':{test_port}' if test_port not in [80, 443] else ''
                    port_url = f'{protocol}://{host}{port_str}'
                    
                    for endpoint in ['/capture', '/snapshot', '/image', '/']:
                        try:
                            test_url = port_url + endpoint
                            response = requests.get(test_url, timeout=5)
                            if response.status_code == 200:
                                content_type = response.headers.get('Content-Type', '')
                                if 'image/' in content_type:
                                    frame = response.content
                                    break
                        except Exception as e:
                            continue
                    if frame:
                        break
                
                if frame:
                    self._update_frame(frame)
                    frame_count += 1
                    
                    current_time = time.time()
                    if current_time - last_time >= 1:
                        self.stats['fps'] = frame_count
                        frame_count = 0
                        last_time = current_time
                        
            except Exception as e:
                self.last_error = str(e)
                self.stats['errors'] += 1
                time.sleep(0.5)
            
            time.sleep(0.1)
    
    def _process_mjpeg_stream(self, response):
        """处理MJPEG流"""
        boundary = None
        content_type = response.headers.get('Content-Type', '')
        
        if 'boundary=' in content_type:
            boundary = content_type.split('boundary=')[1].strip('"')
        
        if not boundary:
            boundary = b'--frame'
        else:
            boundary = boundary.encode('utf-8')
        
        buffer = b''
        frame_start = b'\xff\xd8'
        frame_end = b'\xff\xd9'
        
        for chunk in response.iter_content(chunk_size=8192):
            if not self.running:
                break
                
            buffer += chunk
            
            start_idx = buffer.find(frame_start)
            end_idx = buffer.find(frame_end, start_idx if start_idx != -1 else 0)
            
            if start_idx != -1 and end_idx != -1:
                frame = buffer[start_idx:end_idx+2]
                buffer = buffer[end_idx+2:]
                
                self._update_frame(frame)
    
    def _update_frame(self, frame_data):
        """更新当前帧"""
        with cache_lock:
            self.current_frame = frame_data
            self.stats['frames_received'] += 1
            self.stats['last_frame_time'] = time.time()
    
    def get_current_frame(self):
        """获取当前帧"""
        with cache_lock:
            return self.current_frame
    
    def get_stats(self):
        """获取统计信息"""
        with cache_lock:
            return self.stats.copy()

# 全局代理实例字典
proxies = {}
proxies_lock = threading.Lock()

@esp32_bp.route('/proxy/<path:camera_url>/status')
def proxy_status(camera_url):
    """获取代理状态"""
    url = 'http://' + camera_url if not camera_url.startswith('http') else camera_url
    
    with proxies_lock:
        if url in proxies:
            proxy = proxies[url]
            stats = proxy.get_stats()
            return jsonify({
                'success': True,
                'running': proxy.running,
                'stats': stats,
                'last_error': proxy.last_error
            })
        else:
            return jsonify({
                'success': True,
                'running': False,
                'stats': None
            })

@esp32_bp.route('/proxy/<path:camera_url>/start', methods=['POST'])
def start_proxy(camera_url):
    """启动代理"""
    url = 'http://' + camera_url if not camera_url.startswith('http') else camera_url
    
    with proxies_lock:
        if url not in proxies:
            proxies[url] = ESP32CameraProxy(url)
        
        proxy = proxies[url]
        proxy.start()
    
    return jsonify({
        'success': True,
        'message': 'Proxy started',
        'url': url
    })

@esp32_bp.route('/proxy/<path:camera_url>/stop', methods=['POST'])
def stop_proxy(camera_url):
    """停止代理"""
    url = 'http://' + camera_url if not camera_url.startswith('http') else camera_url
    
    with proxies_lock:
        if url in proxies:
            proxy = proxies[url]
            proxy.stop()
            del proxies[url]
    
    return jsonify({
        'success': True,
        'message': 'Proxy stopped'
    })

@esp32_bp.route('/proxy/<path:camera_url>/stream')
def proxy_stream(camera_url):
    """代理视频流 - MJPEG格式"""
    url = 'http://' + camera_url if not camera_url.startswith('http') else camera_url
    
    with proxies_lock:
        if url not in proxies:
            proxies[url] = ESP32CameraProxy(url)
            proxies[url].start()
        
        proxy = proxies[url]
    
    def generate():
        boundary = b'--frame'
        while True:
            frame = proxy.get_current_frame()
            if frame:
                yield boundary + b'\r\n'
                yield b'Content-Type: image/jpeg\r\n'
                yield b'Content-Length: ' + str(len(frame)).encode('utf-8') + b'\r\n'
                yield b'\r\n'
                yield frame
                yield b'\r\n'
            else:
                time.sleep(0.1)
    
    return Response(
        generate(),
        mimetype='multipart/x-mixed-replace; boundary=frame',
        headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
    )

@esp32_bp.route('/proxy/<path:camera_url>/snapshot')
def proxy_snapshot(camera_url):
    """代理单帧图像"""
    url = 'http://' + camera_url if not camera_url.startswith('http') else camera_url
    
    with proxies_lock:
        if url not in proxies:
            proxies[url] = ESP32CameraProxy(url)
            proxies[url].start()
        
        proxy = proxies[url]
    
    frame = proxy.get_current_frame()
    
    if frame:
        return Response(
            frame,
            mimetype='image/jpeg',
            headers={
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
        )
    else:
        try:
            endpoints = ['/', '/snapshot', '/image', '/capture']
            for endpoint in endpoints:
                try:
                    test_url = url.rstrip('/') + endpoint
                    response = requests.get(test_url, timeout=5)
                    if response.status_code == 200 and 'image/' in response.headers.get('Content-Type', ''):
                        return Response(
                            response.content,
                            mimetype=response.headers.get('Content-Type', 'image/jpeg')
                        )
                except:
                    continue
        except Exception as e:
            pass
        
        return jsonify({'success': False, 'error': 'No frame available'}), 404

@esp32_bp.route('/proxy/<path:camera_url>/test', methods=['GET', 'POST'])
def test_connection(camera_url):
    """测试连接"""
    url = 'http://' + camera_url if not camera_url.startswith('http') else camera_url
    
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        host = parsed.hostname
        protocol = parsed.scheme
        port = parsed.port
        if not port:
            port = 443 if protocol == 'https' else 80
    except:
        host = url.split('/')[2] if '//' in url else url.split('/')[0]
        protocol = 'http'
        port = 80
    
    test_ports = [port, port + 1] if isinstance(port, int) else [port]
    endpoints = ['/stream', '/', '/capture', '/snapshot', '/image', '/video', '/camera']
    
    results = {
        'success': False,
        'url': url,
        'tests': [],
        'working_endpoint': None
    }
    
    for test_port in test_ports:
        port_str = f':{test_port}' if test_port not in [80, 443] else ''
        port_url = f'{protocol}://{host}{port_str}'
        
        for endpoint in endpoints:
            test_url = port_url + endpoint
            test_result = {
                'url': test_url,
                'status': 'testing',
                'status_code': None,
                'content_type': None,
                'error': None
            }
            
            try:
                response = requests.get(test_url, timeout=3)
                test_result['status_code'] = response.status_code
                test_result['content_type'] = response.headers.get('Content-Type', '')
                
                if response.status_code == 200:
                    content_type = test_result['content_type'].lower()
                    if 'multipart/x-mixed-replace' in content_type:
                        test_result['status'] = 'stream'
                        results['success'] = True
                        results['working_endpoint'] = {
                            'url': test_url,
                            'type': 'mjpeg'
                        }
                    elif 'image/' in content_type:
                        test_result['status'] = 'image'
                        if not results['working_endpoint']:
                            results['working_endpoint'] = {
                                'url': test_url,
                                'type': 'image'
                            }
                    elif 'text/html' in content_type:
                        test_result['status'] = 'html'
                    else:
                        test_result['status'] = 'ok'
                else:
                    test_result['status'] = 'error'
            except Exception as e:
                test_result['status'] = 'error'
                test_result['error'] = str(e)
            
            results['tests'].append(test_result)
    
    return jsonify(results)

@esp32_bp.route('/diagnose', methods=['POST'])
def diagnose_esp32():
    """ESP32摄像头诊断API"""
    data = request.get_json()
    url = data.get('url', '')
    
    if not url:
        return jsonify({
            'success': False,
            'error': '请提供ESP32摄像头地址'
        }), 400
    
    if not url.startswith('http://') and not url.startswith('https://'):
        url = 'http://' + url
    
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        host = parsed.hostname
        protocol = parsed.scheme
        port = parsed.port
        if not port:
            port = 443 if protocol == 'https' else 80
    except:
        return jsonify({
            'success': False,
            'error': 'URL解析失败'
        }), 400
    
    results = {
        'success': False,
        'host': host,
        'port': port,
        'network': {},
        'http': {},
        'video': {},
        'recommendations': []
    }
    
    try:
        system = platform.system()
        
        if system == 'Windows':
            ping_cmd = ['ping', '-n', '2', host]
        else:
            ping_cmd = ['ping', '-c', '2', host]
        
        ping_result = subprocess.run(
            ping_cmd,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        results['network']['ping_success'] = ping_result.returncode == 0
        results['network']['ping_output'] = ping_result.stdout
        if ping_result.returncode != 0:
            results['recommendations'].append('网络连接失败，请检查ESP32是否已连接到同一网络')
        
    except Exception as e:
        results['network']['error'] = str(e)
        results['recommendations'].append('无法执行网络诊断')
    
    test_ports = [port, port + 1] if isinstance(port, int) else [port]
    endpoints = ['/stream', '/', '/capture', '/snapshot', '/image', '/status']
    
    found_stream = False
    found_image = False
    
    for test_port in test_ports:
        port_str = f':{test_port}' if test_port not in [80, 443] else ''
        port_url = f'{protocol}://{host}{port_str}'
        
        for endpoint in endpoints:
            test_url = port_url + endpoint
            try:
                response = requests.get(test_url, timeout=5)
                status_code = response.status_code
                content_type = response.headers.get('Content-Type', '')
                
                if status_code == 200:
                    results['http'][test_url] = {
                        'status': 'ok',
                        'content_type': content_type
                    }
                    
                    if 'multipart/x-mixed-replace' in content_type.lower():
                        found_stream = True
                        results['video']['mjpeg_url'] = test_url
                        results['video']['mjpeg_available'] = True
                    elif 'image/' in content_type.lower():
                        found_image = True
                        if 'snapshot_url' not in results['video']:
                            results['video']['snapshot_url'] = test_url
                            results['video']['snapshot_available'] = True
                            
                else:
                    results['http'][test_url] = {
                        'status': 'error',
                        'status_code': status_code
                    }
                    
            except Exception as e:
                results['http'][test_url] = {
                    'status': 'exception',
                    'error': str(e)
                }
    
    if not found_stream and not found_image:
        results['recommendations'].append('未找到视频流端点，请尝试端口 ' + str(port + 1))
        results['recommendations'].append('确认ESP32固件正常运行')
    elif not found_stream and found_image:
        results['recommendations'].append('找到单帧图像，但未找到MJPEG流')
        results['recommendations'].append('将使用单帧轮询模式')
    else:
        results['success'] = True
        results['recommendations'].append('诊断完成，可正常使用')
    
    return jsonify(results)