#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask
from dotenv import load_dotenv
import logging
import os

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 初始化Flask应用
app = Flask(__name__)

# 加载配置
from config import Config
app.config.from_object(Config)

# 导入路由
from app.routes import main
from app.routes import esp32

# 注册蓝图
app.register_blueprint(main.bp)
app.register_blueprint(esp32.esp32_bp, url_prefix='/esp32')

