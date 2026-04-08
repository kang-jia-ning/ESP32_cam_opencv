#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import numpy as np
import requests
from flask import Blueprint, request, jsonify, render_template
from ultralytics import YOLO
from twilio.rest import Client
from app import logger
from config import Config

# 创建蓝图
bp = Blueprint('main', __name__)

# 加载YOLOv8模型
try:
    model = YOLO(Config.YOLO_MODEL_PATH)
    logger.info(f"YOLOv8模型加载成功: {Config.YOLO_MODEL_PATH}")
except Exception as e:
    logger.error(f"YOLOv8模型加载失败: {str(e)}")
    model = None

@bp.route('/', methods=['GET'])
def index():
    """
    主页路由，渲染HTML模板
    """
    return render_template('index.html')

@bp.route('/api/detect', methods=['POST'])
def detect():
    """
    目标检测API端点
    接收ESP32上传的图像，使用YOLOv8进行目标检测，返回检测结果和语音播报文本
    """
    try:
        # 检查是否有文件上传
        if 'image' not in request.files:
            return jsonify({
                'status': 'error',
                'message': '未检测到图像文件'
            }), 400
        
        # 获取上传的图像文件
        image_file = request.files['image']
        
        # 检查文件是否为空
        if image_file.filename == '':
            return jsonify({
                'status': 'error',
                'message': '未选择图像文件'
            }), 400
        
        # 读取图像数据
        image_bytes = image_file.read()
        
        # 使用OpenCV读取图像
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return jsonify({
                'status': 'error',
                'message': '无法读取图像数据'
            }), 400
        
        # 检查模型是否加载成功
        if model is None:
            return jsonify({
                'status': 'error',
                'message': 'YOLOv8模型未加载成功'
            }), 500
        
        # 运行YOLOv8推理
        results = model(img, conf=Config.YOLO_CONF_THRESHOLD, iou=Config.YOLO_IOU_THRESHOLD)
        
        # 解析检测结果
        detections = []
        announcement_texts = []
        
        # 获取图像尺寸
        img_height, img_width = img.shape[:2]
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                # 获取类别ID和置信度
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])
                
                # 获取类别名称
                class_name = result.names[class_id]
                
                # 只处理关键目标类别
                if class_name in Config.KEY_CLASSES:
                    # 获取边界框坐标
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    
                    # 计算目标中心点
                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2
                    
                    # 计算目标在图像中的位置（用于语音播报）
                    # 水平位置：左、中、右
                    if center_x < img_width * 0.33:
                        horizontal_pos = '左'
                    elif center_x > img_width * 0.66:
                        horizontal_pos = '右'
                    else:
                        horizontal_pos = '正'
                    
                    # 垂直位置：前、中、后（根据y坐标和高度）
                    if center_y < img_height * 0.5:
                        vertical_pos = '前'
                    elif center_y > img_height * 0.75:
                        vertical_pos = '近'
                    else:
                        vertical_pos = '中'
                    
                    # 生成语音播报文本
                    chinese_class = Config.KEY_CLASSES[class_name]
                    announcement_texts.append(f"{horizontal_pos}{vertical_pos}方检测到{chinese_class}")
                    
                    # 保存检测结果
                    detections.append({
                        'class': class_name,
                        'chinese_class': chinese_class,
                        'confidence': round(confidence, 2),
                        'bbox': [x1, y1, x2, y2],
                        'position': f"{horizontal_pos}{vertical_pos}方"
                    })
        
        # 如果没有检测到关键目标
        if not announcement_texts:
            announcement_texts.append("当前视野内未检测到关键目标")
        
        # 生成最终的语音播报文本
        final_announcement = '，'.join(announcement_texts)
        
        # 返回检测结果
        return jsonify({
            'status': 'success',
            'detections': detections,
            'announcement': final_announcement,
            'count': len(detections)
        })
        
    except Exception as e:
        logger.error(f"目标检测失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'目标检测失败: {str(e)}'
        }), 500

@bp.route('/api/location', methods=['GET'])
def get_location():
    """
    IP定位API端点
    获取请求方的公网IP地址，使用高德地图API查询地理位置信息并返回
    """
    try:
        # 获取请求方的IP地址
        # 如果使用了代理，从X-Forwarded-For头获取真实IP
        if 'X-Forwarded-For' in request.headers:
            client_ip = request.headers['X-Forwarded-For'].split(',')[0].strip()
        else:
            client_ip = request.remote_addr
        
        logger.info(f"获取位置信息，请求IP: {client_ip}")
        
        # 检查是否通过前端传递了GPS经纬度
        lat = request.args.get('lat')
        lon = request.args.get('lon')
        
        location_info = {}
        
        if lat and lon:
            # 使用GPS经纬度进行逆地理编码
            logger.info(f"使用GPS经纬度定位: lat={lat}, lon={lon}")
            
            # 调用高德地图逆地理编码API
            params = {
                'key': Config.AMAP_API_KEY,
                'location': f"{lon},{lat}",  # 高德API要求格式为：经度,纬度
                'extensions': 'base',
                'batch': 'false',
                'roadlevel': '0'
            }
            
            response = requests.get(Config.AMAP_GEOCODE_URL, params=params, timeout=10)
            geocode_data = response.json()
            
            if geocode_data['status'] == '1' and geocode_data['regeocode']:
                regeocode = geocode_data['regeocode']
                address_component = regeocode.get('addressComponent', {})
                
                location_info = {
                    'country': address_component.get('country', ''),
                    'region': address_component.get('province', ''),
                    'city': address_component.get('city', ''),
                    'district': address_component.get('district', ''),
                    'street': address_component.get('street', ''),
                    'street_number': address_component.get('streetNumber', {}).get('number', ''),
                    'lat': float(lat),
                    'lon': float(lon),
                    'address': regeocode.get('formatted_address', ''),
                    'ip': client_ip
                }
            else:
                logger.error(f"高德地图逆地理编码失败: {geocode_data}")
                return jsonify({
                    'status': 'error',
                    'message': 'GPS定位失败'
                }), 500
        else:
            # 使用IP定位
            logger.info(f"使用IP定位: {client_ip}")
            
            # 使用高德地图IP定位API
            params = {
                'key': Config.AMAP_API_KEY,
                'ip': client_ip,
                'output': 'json'
            }
            
            logger.info(f"调用高德地图IP定位API，URL: {Config.AMAP_IP_LOCATION_URL}, 参数: {params}")
            
            try:
                response = requests.get(Config.AMAP_IP_LOCATION_URL, params=params, timeout=10)
                logger.info(f"高德地图IP定位API响应状态码: {response.status_code}")
                logger.info(f"高德地图IP定位API响应内容: {response.text}")
                
                location_data = response.json()
                
                if location_data['status'] == '1':
                    # 提取关键位置信息
                    location_info = {
                        'country': location_data.get('country', ''),
                        'region': location_data.get('province', ''),
                        'city': location_data.get('city', ''),
                        'lat': float(location_data.get('lat', 0)),
                        'lon': float(location_data.get('lon', 0)),
                        'isp': location_data.get('isp', ''),
                        'ip': client_ip
                    }
                else:
                    logger.error(f"高德地图IP定位失败: {location_data}")
                    return jsonify({
                        'status': 'error',
                        'message': 'IP定位失败',
                        'error_details': location_data
                    }), 500
            except requests.exceptions.RequestException as e:
                logger.error(f"高德地图IP定位API请求异常: {str(e)}")
                return jsonify({
                    'status': 'error',
                    'message': '网络异常，无法获取位置信息',
                    'error_details': str(e)
                }), 500
        
        # 生成语音播报文本
        if location_info.get('city'):
            announcement = f"您当前在{location_info['city']}附近"
        elif location_info.get('region'):
            announcement = f"您当前在{location_info['region']}附近"
        elif location_info.get('country'):
            announcement = f"您当前在{location_info['country']}附近"
        else:
            announcement = "无法获取具体位置信息"
        
        logger.info(f"定位成功: {location_info}")
        
        return jsonify({
            'status': 'success',
            'location': location_info,
            'announcement': announcement
        })
        
    except requests.exceptions.Timeout as e:
        logger.error(f"定位请求超时: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': '定位服务响应超时，请稍后重试'
        }), 500
    except requests.exceptions.RequestException as e:
        logger.error(f"定位请求失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': '网络异常，无法获取位置信息'
        }), 500
    except Exception as e:
        logger.error(f"定位处理失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'定位处理失败: {str(e)}'
        }), 500

@bp.route('/api/weather', methods=['GET'])
def get_weather():
    """
    天气查询API端点
    根据经纬度或城市名称查询实时天气信息
    """
    try:
        # 获取查询参数
        lat = request.args.get('lat')
        lon = request.args.get('lon')
        city = request.args.get('city')
        
        logger.info(f"获取天气信息，lat: {lat}, lon: {lon}, city: {city}")
        
        params = {
            'key': Config.AMAP_API_KEY,
            'output': 'json',
            'extensions': 'all'  # 返回详细天气信息
        }
        
        if lat and lon:
            # 使用经纬度查询天气：先通过逆地理编码获取城市名称
            logger.info(f"使用经纬度查询天气: lat={lat}, lon={lon}")
            try:
                # 调用逆地理编码API获取城市信息
                geocode_params = {
                    'key': Config.AMAP_API_KEY,
                    'location': f"{lon},{lat}",  # 高德API要求格式为：经度,纬度
                    'extensions': 'base',
                    'output': 'json'
                }
                
                geocode_response = requests.get(Config.AMAP_GEOCODE_URL, params=geocode_params, timeout=10)
                geocode_data = geocode_response.json()
                
                if geocode_data['status'] == '1' and geocode_data.get('regeocode'):
                    city_name = geocode_data['regeocode'].get('addressComponent', {}).get('city', '')
                    if not city_name:
                        # 如果没有城市名，使用区县名
                        city_name = geocode_data['regeocode'].get('addressComponent', {}).get('district', '')
                    
                    if city_name:
                        logger.info(f"逆地理编码获取到城市名: {city_name}")
                        params['city'] = city_name
                    else:
                        logger.warning("逆地理编码未能获取到有效城市名，直接使用经纬度查询")
                        params['location'] = f"{lon},{lat}"
                else:
                    logger.warning(f"逆地理编码失败: {geocode_data}")
                    params['location'] = f"{lon},{lat}"
                    
            except Exception as e:
                logger.error(f"逆地理编码异常: {str(e)}")
                params['location'] = f"{lon},{lat}"
        elif city:
            # 使用城市名称查询天气
            logger.info(f"使用城市名称查询天气: {city}")
            params['city'] = city
        else:
            # 没有提供查询参数，使用IP定位获取当前位置
            logger.info("没有提供查询参数，使用IP定位获取当前位置")
            
            # 重构：提取位置获取逻辑为单独的函数
            def get_current_location():
                """获取当前位置信息"""
                # 获取请求方的IP地址
                if 'X-Forwarded-For' in request.headers:
                    client_ip = request.headers['X-Forwarded-For'].split(',')[0].strip()
                else:
                    client_ip = request.remote_addr
                
                # 使用高德地图IP定位API
                ip_params = {
                    'key': Config.AMAP_API_KEY,
                    'ip': client_ip,
                    'output': 'json'
                }
                
                ip_response = requests.get(Config.AMAP_IP_LOCATION_URL, params=ip_params, timeout=10)
                ip_data = ip_response.json()
                
                if ip_data['status'] == '1':
                    return {
                        'lat': float(ip_data.get('lat', 0)),
                        'lon': float(ip_data.get('lon', 0)),
                        'city': ip_data.get('city', '')
                    }
                return None
            
            # 获取当前位置
            current_location = get_current_location()
            if current_location:
                params['location'] = f"{current_location['lon']},{current_location['lat']}"
            else:
                return jsonify({
                    'status': 'error',
                    'message': '无法获取当前位置，无法查询天气'
                }), 500
        
        # 调用高德地图天气API获取实时天气
        response = requests.get(Config.AMAP_WEATHER_URL, params=params, timeout=10)
        weather_data = response.json()
        
        if weather_data['status'] == '1':
            # 处理实时天气数据（lives字段）
            if 'lives' in weather_data and weather_data['lives']:
                live_weather = weather_data['lives'][0]
            else:
                # 如果没有实时数据，使用预报数据的第一条
                if 'forecasts' in weather_data and weather_data['forecasts']:
                    forecast_data = weather_data['forecasts'][0]
                    # 将预报数据转换为实时格式
                    live_weather = {
                        'city': forecast_data.get('city', ''),
                        'province': forecast_data.get('province', ''),
                        'reporttime': forecast_data.get('reporttime', ''),
                        'weather': forecast_data.get('casts', [{}])[0].get('dayweather', ''),
                        'temperature': forecast_data.get('casts', [{}])[0].get('daytemp', ''),
                        'humidity': '',  # 预报数据中没有湿度
                        'winddirection': forecast_data.get('casts', [{}])[0].get('daywind', ''),
                        'windpower': forecast_data.get('casts', [{}])[0].get('daypower', ''),
                        'pressure': '',
                        'visibility': '',
                        'dew': ''
                    }
                else:
                    logger.error(f"高德地图天气查询无有效数据: {weather_data}")
                    return jsonify({
                        'status': 'error',
                        'message': '天气查询无有效数据'
                    }), 500
            
            # 提取预报天气信息（如果有）
            if 'forecasts' in weather_data and weather_data['forecasts']:
                forecast_info = weather_data['forecasts'][0]
            else:
                forecast_info = {}
            
            # 构建天气信息
            weather_info = {
                'basic': {
                    'city': live_weather.get('city', ''),
                    'province': live_weather.get('province', ''),
                    'update_time': live_weather.get('reporttime', '')
                },
                'now': {
                    'weather': live_weather.get('weather', ''),
                    'temperature': live_weather.get('temperature', ''),
                    'humidity': live_weather.get('humidity', ''),
                    'wind_direction': live_weather.get('winddirection', ''),
                    'wind_power': live_weather.get('windpower', ''),
                    'pressure': live_weather.get('pressure', ''),
                    'visibility': live_weather.get('visibility', ''),
                    'dew_point': live_weather.get('dew', '')
                },
                'forecast': forecast_info
            }
            
            # 生成语音播报文本
            announcement = f"当前{weather_info['basic']['city']}的天气状况是{weather_info['now']['weather']}，温度{weather_info['now']['temperature']}度，湿度{weather_info['now']['humidity']}%，{weather_info['now']['wind_direction']}风{weather_info['now']['wind_power']}级"
            
            logger.info(f"天气查询成功: {weather_info}")
            
            return jsonify({
                'status': 'success',
                'weather': weather_info,
                'announcement': announcement
            })
        else:
            logger.error(f"高德地图天气查询失败: {weather_data}")
            return jsonify({
                'status': 'error',
                'message': '天气查询失败'
            }), 500
        
    except requests.exceptions.Timeout as e:
        logger.error(f"天气请求超时: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': '天气服务响应超时，请稍后重试'
        }), 500
    except requests.exceptions.RequestException as e:
        logger.error(f"天气请求失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': '网络异常，无法获取天气信息'
        }), 500
    except Exception as e:
        logger.error(f"天气处理失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'天气处理失败: {str(e)}'
        }), 500

@bp.route('/api/emergency', methods=['POST'])
def emergency_call():
    """
    紧急联系人呼叫API端点
    向预设的紧急联系人发送求助短信，包含位置信息
    """
    try:
        logger.info("收到紧急求助请求")
        
        # 获取请求方的IP地址
        if 'X-Forwarded-For' in request.headers:
            client_ip = request.headers['X-Forwarded-For'].split(',')[0].strip()
        else:
            client_ip = request.remote_addr
        
        # 获取位置信息
        location_info = None
        location_text = "位置未知"
        
        try:
            # 调用ip-api.com获取位置信息
            ip_api_url = f"http://ip-api.com/json/{client_ip}?lang=zh-CN"
            response = requests.get(ip_api_url, timeout=5)
            location_data = response.json()
            
            if location_data['status'] == 'success':
                city = location_data.get('city', '')
                region = location_data.get('regionName', '')
                country = location_data.get('country', '')
                
                # 构建位置文本
                if city:
                    location_text = f"{city}"
                elif region:
                    location_text = f"{region}"
                elif country:
                    location_text = f"{country}"
                
                location_info = location_data
        except Exception as e:
            logger.error(f"获取位置信息失败: {str(e)}")
        
        # 构建求助短信内容
        message_body = f"紧急求助：我可能在{location_text}附近遇到麻烦，请尽快联系我。"
        
        # 检查是否配置了紧急联系人
        if not Config.EMERGENCY_CONTACTS or Config.EMERGENCY_CONTACTS == ['']:
            logger.warning("未配置紧急联系人")
            return jsonify({
                'status': 'warning',
                'message': '未配置紧急联系人，请在环境变量中设置EMERGENCY_CONTACTS',
                'location': location_info
            }), 200
        
        # 检查是否配置了Twilio
        if Config.TWILIO_ACCOUNT_SID == 'YOUR_ACCOUNT_SID' or Config.TWILIO_AUTH_TOKEN == 'YOUR_AUTH_TOKEN':
            logger.warning("Twilio未正确配置")
            return jsonify({
                'status': 'warning',
                'message': 'Twilio未正确配置，请在环境变量中设置Twilio凭证',
                'location': location_info,
                'message_body': message_body
            }), 200
        
        # 初始化Twilio客户端
        client = Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)
        
        # 发送短信给所有紧急联系人
        sent_count = 0
        for contact in Config.EMERGENCY_CONTACTS:
            contact = contact.strip()
            if contact:
                try:
                    message = client.messages.create(
                        body=message_body,
                        from_=Config.TWILIO_PHONE_NUMBER,
                        to=contact
                    )
                    logger.info(f"已向{contact}发送求助短信，消息ID: {message.sid}")
                    sent_count += 1
                except Exception as e:
                    logger.error(f"向{contact}发送短信失败: {str(e)}")
        
        if sent_count > 0:
            return jsonify({
                'status': 'success',
                'message': '求助信息已发送',
                'sent_count': sent_count,
                'location': location_info
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '无法发送求助信息，请检查Twilio配置和联系人号码',
                'location': location_info
            }), 500
            
    except Exception as e:
        logger.error(f"紧急求助处理失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'紧急求助处理失败: {str(e)}'
        }), 500

@bp.route('/api/ask', methods=['POST'])
def ask_question():
    """
    智能问答API端点
    接收文本问题和可选的图像，调用大语言模型API，返回回答，结合位置上下文信息
    """
    try:
        # 处理文本问题
        question = ""
        if request.is_json:
            data = request.get_json()
            if data and 'question' in data:
                question = data['question'].strip()
        else:
            # 从表单数据获取问题
            question = request.form.get('question', '').strip()
        
        if not question:
            return jsonify({
                'status': 'error',
                'message': '问题不能为空'
            }), 400
        
        logger.info(f"收到问题: {question}")
        
        # 处理图像（如果有）
        image_url = None
        if 'image' in request.files:
            image_file = request.files['image']
            if image_file and image_file.filename != '':
                # 这里可以根据需要将图像上传到云存储并获取URL
                # 目前仅作为示例，实际项目中需要实现图像上传逻辑
                logger.info(f"收到图像: {image_file.filename}")
                # 注意：豆包API需要图像URL，这里需要实现图像上传功能
                # 暂时跳过图像处理，仅记录日志
        
        # 获取请求方的IP地址
        if 'X-Forwarded-For' in request.headers:
            client_ip = request.headers['X-Forwarded-For'].split(',')[0].strip()
        else:
            client_ip = request.remote_addr
        
        # 获取位置信息
        location_text = ""
        
        try:
            # 调用ip-api.com获取位置信息
            ip_api_url = f"http://ip-api.com/json/{client_ip}?lang=zh-CN"
            response = requests.get(ip_api_url, timeout=5)
            location_data = response.json()
            
            if location_data['status'] == 'success':
                city = location_data.get('city', '')
                if city:
                    location_text = city
        except Exception as e:
            logger.error(f"获取位置信息失败: {str(e)}")
        
        # 构建完整的问题，包含位置上下文
        if location_text:
            full_question = f"用户在{location_text}附近，他问：{question}"
        else:
            full_question = question
        
        # 检查是否是天气查询
        import re
        weather_keywords = ['天气', '温度', '湿度', '风力', '风向', '晴', '雨', '雪', '阴', '多云']
        is_weather_query = any(keyword in question for keyword in weather_keywords)
        
        weather_info = None
        if is_weather_query:
            logger.info("检测到天气查询，获取天气信息")
            try:
                # 调用天气API获取天气信息
                weather_response = requests.get(f"http://localhost:5000/api/weather?city={location_text}", timeout=10)
                weather_data = weather_response.json()
                
                if weather_data['status'] == 'success':
                    weather_info = weather_data['weather']
                    weather_announcement = weather_data['announcement']
                    logger.info(f"获取天气信息成功: {weather_info}")
                    # 将天气信息添加到问题中，让AI助手参考
                    full_question += f"\n\n当前天气信息：{weather_announcement}"
            except Exception as e:
                logger.error(f"获取天气信息失败: {str(e)}")
        
        # 检查是否配置了豆包API密钥，如果配置了则使用豆包API
        if Config.DOUBAO_API_KEY != 'YOUR_DOUBAO_API_KEY':
            logger.info("使用豆包API进行智能问答")
            try:
                # 调用豆包API
                doubao_url = Config.DOUBAO_API_URL
                headers = {
                    "Authorization": f"Bearer {Config.DOUBAO_API_KEY}",
                    "Content-Type": "application/json"
                }
                
                # 构建消息内容，支持多模态
                user_message_content = []
                
                # 如果有图像URL，添加到消息内容中
                if image_url:
                    user_message_content.append({
                        "image_url": {
                            "url": image_url
                        },
                        "type": "image_url"
                    })
                
                # 添加文本内容
                user_message_content.append({
                    "text": full_question,
                    "type": "text"
                })
                
                payload = {
                    "model": Config.DOUBAO_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": "你是一个为视障人士提供帮助的智能助手，回答要简洁明了，适合语音播报。"
                        },
                        {
                            "role": "user",
                            "content": user_message_content
                        }
                    ],
                    "temperature": 0.7,
                    "max_completion_tokens": 65535,
                    "reasoning_effort": "medium"
                }
                
                # 创建会话并禁用代理
                session = requests.Session()
                session.trust_env = False  # 禁用环境变量中的代理设置
                
                # 优化请求参数
                payload['max_completion_tokens'] = 2000  # 减少生成的tokens数量，提高响应速度
                
                # 实现重试机制
                import time
                max_retries = 3
                retry_delay = 1  # 初始重试延迟
                response = None
                
                for attempt in range(max_retries):
                    try:
                        start_time = time.time()
                        # 增加超时时间到30秒
                        response = session.post(doubao_url, headers=headers, json=payload, timeout=30)
                        end_time = time.time()
                        response_time = end_time - start_time
                        logger.info(f"豆包API调用成功，响应时间: {response_time:.2f}秒，尝试次数: {attempt + 1}")
                        
                        response_data = response.json()
                        
                        if response.status_code != 200:
                            logger.error(f"豆包API调用失败: {response_data}")
                            return jsonify({
                                'status': 'error',
                                'message': '大语言模型API调用失败',
                                'error_details': response_data
                            }), 500
                        
                        # 提取回答
                        answer = response_data['choices'][0]['message']['content'].strip()
                        
                        logger.info(f"问题回答: {answer}")
                        
                        return jsonify({
                            'status': 'success',
                            'answer': answer,
                            'question': question,
                            'location': location_text
                        })
                    except requests.exceptions.Timeout:
                        logger.warning(f"豆包API调用超时，尝试次数: {attempt + 1}/{max_retries}")
                        if attempt < max_retries - 1:
                            # 指数退避重试
                            time.sleep(retry_delay)
                            retry_delay *= 2
                        else:
                            # 所有重试都失败
                            logger.error("豆包API调用多次超时，已达到最大重试次数")
                            # 降级策略：返回模拟回答
                            mock_answer = f"抱歉，当前服务响应较慢。您的问题是：{question}"
                            if location_text:
                                mock_answer += f"（您当前在{location_text}附近）"
                            
                            return jsonify({
                                'status': 'warning',
                                'message': '大语言模型服务响应超时，返回模拟回答',
                                'answer': mock_answer,
                                'question': question,
                                'location': location_text
                            }), 200
                    except Exception as e:
                        logger.error(f"豆包API调用异常，尝试次数: {attempt + 1}/{max_retries}，错误: {str(e)}")
                        if attempt < max_retries - 1:
                            # 指数退避重试
                            time.sleep(retry_delay)
                            retry_delay *= 2
                        else:
                            # 所有重试都失败
                            logger.error(f"豆包API调用多次异常，已达到最大重试次数，错误: {str(e)}")
                            # 降级策略：返回模拟回答
                            mock_answer = f"抱歉，当前服务暂时不可用。您的问题是：{question}"
                            if location_text:
                                mock_answer += f"（您当前在{location_text}附近）"
                            
                            return jsonify({
                                'status': 'warning',
                                'message': '大语言模型服务暂时不可用，返回模拟回答',
                                'answer': mock_answer,
                                'question': question,
                                'location': location_text
                            }), 200
                
            except Exception as e:
                logger.error(f"调用豆包API失败: {str(e)}")
                return jsonify({
                    'status': 'error',
                    'message': f'调用豆包API失败: {str(e)}'
                }), 500
        # 检查是否配置了OpenAI API密钥
        elif Config.OPENAI_API_KEY != 'YOUR_OPENAI_API_KEY':
            logger.info("使用OpenAI API进行智能问答")
            try:
                # 调用OpenAI API
                openai_url = "https://api.openai.com/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {Config.OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {
                            "role": "system",
                            "content": "你是一个为视障人士提供帮助的智能助手，回答要简洁明了，适合语音播报。"
                        },
                        {
                            "role": "user",
                            "content": full_question
                        }
                    ],
                    "temperature": 0.7,
                    "max_tokens": 150
                }
                
                # 创建会话并禁用代理
                session = requests.Session()
                session.trust_env = False  # 禁用环境变量中的代理设置
                
                response = session.post(openai_url, headers=headers, json=payload, timeout=10)
                response_data = response.json()
                
                if response.status_code != 200:
                    logger.error(f"OpenAI API调用失败: {response_data}")
                    return jsonify({
                        'status': 'error',
                        'message': '大语言模型API调用失败',
                        'error_details': response_data
                    }), 500
                
                # 提取回答
                answer = response_data['choices'][0]['message']['content'].strip()
                
                logger.info(f"问题回答: {answer}")
                
                return jsonify({
                    'status': 'success',
                    'answer': answer,
                    'question': question,
                    'location': location_text
                })
                
            except Exception as e:
                logger.error(f"调用OpenAI API失败: {str(e)}")
                return jsonify({
                    'status': 'error',
                    'message': f'调用OpenAI API失败: {str(e)}'
                }), 500
        # 如果都没有配置，则返回模拟回答
        else:
            logger.warning("未配置大语言模型API密钥")
            # 返回模拟回答，用于测试
            mock_answer = f"这是一个模拟回答。您的问题是：{question}"
            if location_text:
                mock_answer += f"（您当前在{location_text}附近）"
            
            return jsonify({
                'status': 'warning',
                'message': '未配置大语言模型API密钥，返回模拟回答',
                'answer': mock_answer,
                'question': question,
                'location': location_text
            }), 200
            
    except Exception as e:
        logger.error(f"智能问答处理失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'智能问答处理失败: {str(e)}'
        }), 500
