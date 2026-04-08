#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
视障人士智能辅助工具后端应用
基于Flask框架，集成YOLOv8目标检测、IP定位、紧急联系人呼叫和智能问答功能
"""

import os
import cv2
import numpy as np
import requests
from flask import Flask, request, jsonify
from ultralytics import YOLO
from twilio.rest import Client
from dotenv import load_dotenv
import logging

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 初始化Flask应用
app = Flask(__name__)

# 加载YOLOv8模型
try:
    # 使用轻量级的YOLOv8n模型
    model = YOLO('yolov8n.pt')
    logger.info("YOLOv8模型加载成功")
except Exception as e:
    logger.error(f"YOLOv8模型加载失败: {str(e)}")
    model = None

# 关键目标类别
KEY_CLASSES = {
    'person': '行人',
    'car': '车辆',
    'bicycle': '自行车',
    'motorcycle': '摩托车',
    'stop sign': '停止标志',
    'traffic light': '交通灯',
    'dog': '狗',
    'cat': '猫'
}

# Twilio配置
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', 'YOUR_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', 'YOUR_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', 'YOUR_TWILIO_PHONE')
EMERGENCY_CONTACTS = os.getenv('EMERGENCY_CONTACTS', '').split(',')

# OpenAI API配置
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', 'YOUR_OPENAI_API_KEY')

# 主页路由
@app.route('/', methods=['GET'])
def index():
    """
    主页路由，用于测试服务器是否正常运行
    """
    return jsonify({
        'status': 'success',
        'message': '视障人士智能辅助工具后端服务正在运行',
        'version': '1.0.0'
    })

@app.route('/emergency', methods=['POST'])
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
        if not EMERGENCY_CONTACTS or EMERGENCY_CONTACTS == ['']:
            logger.warning("未配置紧急联系人")
            return jsonify({
                'status': 'warning',
                'message': '未配置紧急联系人，请在环境变量中设置EMERGENCY_CONTACTS',
                'location': location_info
            }), 200
        
        # 检查是否配置了Twilio
        if TWILIO_ACCOUNT_SID == 'YOUR_ACCOUNT_SID' or TWILIO_AUTH_TOKEN == 'YOUR_AUTH_TOKEN':
            logger.warning("Twilio未正确配置")
            return jsonify({
                'status': 'warning',
                'message': 'Twilio未正确配置，请在环境变量中设置Twilio凭证',
                'location': location_info,
                'message_body': message_body
            }), 200
        
        # 初始化Twilio客户端
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # 发送短信给所有紧急联系人
        sent_count = 0
        for contact in EMERGENCY_CONTACTS:
            contact = contact.strip()
            if contact:
                try:
                    message = client.messages.create(
                        body=message_body,
                        from_=TWILIO_PHONE_NUMBER,
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

@app.route('/location', methods=['GET'])
def get_location():
    """
    IP定位API端点
    获取请求方的公网IP地址，查询地理位置信息并返回
    """
    try:
        # 获取请求方的IP地址
        # 如果使用了代理，从X-Forwarded-For头获取真实IP
        if 'X-Forwarded-For' in request.headers:
            client_ip = request.headers['X-Forwarded-For'].split(',')[0].strip()
        else:
            client_ip = request.remote_addr
        
        logger.info(f"获取位置信息，请求IP: {client_ip}")
        
        # 使用ip-api.com查询地理位置
        # 注意：ip-api.com有请求限制，生产环境中应考虑使用付费服务或其他替代方案
        ip_api_url = f"http://ip-api.com/json/{client_ip}?lang=zh-CN"
        response = requests.get(ip_api_url, timeout=5)
        location_data = response.json()
        
        if location_data['status'] != 'success':
            return jsonify({
                'status': 'error',
                'message': 'IP定位失败'
            }), 500
        
        # 提取关键位置信息
        location_info = {
            'country': location_data.get('country', ''),
            'region': location_data.get('regionName', ''),
            'city': location_data.get('city', ''),
            'zip': location_data.get('zip', ''),
            'lat': location_data.get('lat', 0),
            'lon': location_data.get('lon', 0),
            'isp': location_data.get('isp', ''),
            'ip': client_ip
        }
        
        # 生成语音播报文本
        if location_info['city']:
            announcement = f"您当前在{location_info['city']}附近"
        elif location_info['region']:
            announcement = f"您当前在{location_info['region']}附近"
        elif location_info['country']:
            announcement = f"您当前在{location_info['country']}附近"
        else:
            announcement = "无法获取具体位置信息"
        
        return jsonify({
            'status': 'success',
            'location': location_info,
            'announcement': announcement
        })
        
    except Exception as e:
        logger.error(f"IP定位失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'IP定位失败: {str(e)}'
        }), 500

@app.route('/ask', methods=['POST'])
def ask_question():
    """
    智能问答API端点
    接收文本问题，调用大语言模型API，返回回答，结合位置上下文信息
    """
    try:
        # 获取请求体中的问题
        data = request.get_json()
        if not data or 'question' not in data:
            return jsonify({
                'status': 'error',
                'message': '请求中缺少question字段'
            }), 400
        
        question = data['question'].strip()
        if not question:
            return jsonify({
                'status': 'error',
                'message': '问题不能为空'
            }), 400
        
        logger.info(f"收到问题: {question}")
        
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
        
        # 检查是否配置了OpenAI API密钥
        if OPENAI_API_KEY == 'YOUR_OPENAI_API_KEY':
            logger.warning("OpenAI API密钥未正确配置")
            # 返回模拟回答，用于测试
            mock_answer = f"这是一个模拟回答。您的问题是：{question}"
            if location_text:
                mock_answer += f"（您当前在{location_text}附近）"
            
            return jsonify({
                'status': 'warning',
                'message': 'OpenAI API密钥未正确配置，返回模拟回答',
                'answer': mock_answer,
                'question': question,
                'location': location_text
            }), 200
        
        # 调用OpenAI API
        try:
            openai_url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
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
            
            response = requests.post(openai_url, headers=headers, json=payload, timeout=10)
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
            logger.error(f"调用大语言模型API失败: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': f'调用大语言模型API失败: {str(e)}'
            }), 500
            
    except Exception as e:
        logger.error(f"智能问答处理失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'智能问答处理失败: {str(e)}'
        }), 500

@app.route('/detect', methods=['POST'])
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
        results = model(img, conf=0.5, iou=0.45)
        
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
                if class_name in KEY_CLASSES:
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
                    chinese_class = KEY_CLASSES[class_name]
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

if __name__ == '__main__':
    # 启动Flask服务器
    # 注意：在生产环境中，应该使用Gunicorn或uWSGI等WSGI服务器
    app.run(host='0.0.0.0', port=5000, debug=True)
