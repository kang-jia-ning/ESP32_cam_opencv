#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app import app

if __name__ == '__main__':
    """启动Flask应用"""
    # 注意：在生产环境中，应该使用Gunicorn或uWSGI等WSGI服务器
    app.run(host='0.0.0.0', port=5000, debug=app.config['DEBUG'])
