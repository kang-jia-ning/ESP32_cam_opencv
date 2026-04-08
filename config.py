#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    """应用程序配置类"""
    # Flask配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    # YOLOv8配置
    YOLO_MODEL_PATH = os.environ.get('YOLO_MODEL_PATH') or 'yolov8n.pt'
    YOLO_CONF_THRESHOLD = float(os.environ.get('YOLO_CONF_THRESHOLD') or 0.5)
    YOLO_IOU_THRESHOLD = float(os.environ.get('YOLO_IOU_THRESHOLD') or 0.45)
    
    # Twilio配置
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', 'YOUR_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', 'YOUR_AUTH_TOKEN')
    TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', 'YOUR_TWILIO_PHONE')
    EMERGENCY_CONTACTS = os.environ.get('EMERGENCY_CONTACTS', '').split(',')
    
    # OpenAI API配置
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', 'YOUR_OPENAI_API_KEY')
    
    # 豆包API配置
    DOUBAO_API_KEY = os.environ.get('DOUBAO_API_KEY', 'YOUR_DOBAO_API_KEY')
    DOUBAO_API_URL = os.environ.get('DOUBAO_API_URL', 'https://ark.cn-beijing.volces.com/api/v3/chat/completions')
    DOUBAO_MODEL = os.environ.get('DOUBAO_MODEL', 'doubao-seed-1-6-251015')
    
    # 高德地图API配置
    AMAP_API_KEY = os.environ.get('AMAP_API_KEY', '9e65822eb662f59fce5cec9438237a15')
    AMAP_IP_LOCATION_URL = os.environ.get('AMAP_IP_LOCATION_URL', 'https://restapi.amap.com/v3/ip')
    AMAP_WEATHER_URL = os.environ.get('AMAP_WEATHER_URL', 'https://restapi.amap.com/v3/weather/weatherInfo')
    AMAP_GEOCODE_URL = os.environ.get('AMAP_GEOCODE_URL', 'https://restapi.amap.com/v3/geocode/regeo')
    
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