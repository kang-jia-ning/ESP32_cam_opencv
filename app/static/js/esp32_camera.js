/**
 * ESP32摄像头视频流管理模块 - 简化诊断版
 * 功能：直接连接和诊断ESP32摄像头
 */

class Esp32CameraManager {
    constructor() {
        this.config = {
            defaultUrl: 'http://172.20.10.3/',
            timeout: 10000,
            maxRetries: 3,
            frameInterval: 500
        };

        this.state = {
            isConnecting: false,
            isConnected: false,
            isPlaying: false,
            currentUrl: null,
            imgElement: null,
            canvasElement: null,
            canvasContext: null,
            videoElement: null,
            streamIntervalId: null,
            captureIntervalId: null
        };

        this.callbacks = {
            onConnecting: null,
            onConnected: null,
            onDisconnected: null,
            onFrameReceived: null,
            onError: null,
            onStatusChange: null,
            onLog: null
        };
    }

    /**
     * 初始化摄像头管理器
     */
    init(options = {}) {
        this.canvasElement = options.canvasElement || document.getElementById('canvasElement');
        this.videoElement = options.videoElement || document.getElementById('videoElement');

        if (this.canvasElement) {
            this.canvasContext = this.canvasElement.getContext('2d');
        }

        if (options.onConnecting) this.callbacks.onConnecting = options.onConnecting;
        if (options.onConnected) this.callbacks.onConnected = options.onConnected;
        if (options.onDisconnected) this.callbacks.onDisconnected = options.onDisconnected;
        if (options.onFrameReceived) this.callbacks.onFrameReceived = options.onFrameReceived;
        if (options.onError) this.callbacks.onError = options.onError;
        if (options.onStatusChange) this.callbacks.onStatusChange = options.onStatusChange;
        if (options.onLog) this.callbacks.onLog = options.onLog;
    }

    /**
     * 记录日志
     */
    log(message, type = 'info') {
        console.log(`[Esp32Camera] [${type}] ${message}`);
        if (this.callbacks.onLog) {
            this.callbacks.onLog(message, type);
        }
    }

    /**
     * 诊断ESP32摄像头连接
     */
    async diagnose(url) {
        this.log('开始诊断ESP32摄像头: ' + url, 'info');

        const results = {
            success: false,
            url: url,
            tests: [],
            workingEndpoint: null
        };

        // 解析基础URL
        let baseUrl = url;
        if (!baseUrl.startsWith('http://') && !baseUrl.startsWith('https://')) {
            baseUrl = 'http://' + baseUrl;
        }
        if (baseUrl.endsWith('/')) {
            baseUrl = baseUrl.slice(0, -1);
        }

        // 解析URL获取主机和端口
        let urlObj;
        try {
            urlObj = new URL(baseUrl);
        } catch (e) {
            this.log('URL解析失败: ' + e.message, 'error');
            results.tests.push({
                name: 'URL解析',
                success: false,
                error: e.message
            });
            return results;
        }

        const host = urlObj.hostname;
        const protocol = urlObj.protocol;
        let port = urlObj.port || (protocol === 'https:' ? 443 : 80);

        this.log(`主机: ${host}, 协议: ${protocol}, 端口: ${port}`, 'info');

        // 测试的端口列表
        const testPorts = [parseInt(port)];
        if (!isNaN(parseInt(port))) {
            testPorts.push(parseInt(port) + 1);
        }

        // 测试的端点列表
        const endpoints = [
            '/stream',
            '/',
            '/capture',
            '/snapshot',
            '/image',
            '/video',
            '/camera'
        ];

        // 测试所有组合
        for (const testPort of testPorts) {
            const portStr = (testPort === 80 || testPort === 443) ? '' : `:${testPort}`;
            const testBaseUrl = `${protocol}//${host}${portStr}`;

            for (const endpoint of endpoints) {
                const testUrl = testBaseUrl + endpoint;
                const testResult = await this.testEndpoint(testUrl);

                results.tests.push({
                    name: `${testUrl}`,
                    success: testResult.success,
                    statusCode: testResult.statusCode,
                    contentType: testResult.contentType,
                    error: testResult.error,
                    type: testResult.type
                });

                if (testResult.success) {
                    this.log(`✓ 找到可用端点: ${testUrl} (${testResult.type})`, 'success');
                    results.success = true;
                    results.workingEndpoint = {
                        url: testUrl,
                        type: testResult.type,
                        port: testPort
                    };
                    return results;
                }
            }
        }

        this.log('未找到可用的视频流端点', 'error');
        return results;
    }

    /**
     * 测试单个端点
     */
    async testEndpoint(url) {
        const result = {
            success: false,
            statusCode: null,
            contentType: null,
            error: null,
            type: null
        };

        this.log(`测试端点: ${url}`, 'info');

        try {
            // 首先用Fetch测试
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);

            const response = await fetch(url, {
                method: 'GET',
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            result.statusCode = response.status;
            result.contentType = response.headers.get('Content-Type') || '';

            this.log(`  状态码: ${response.status}, Content-Type: ${result.contentType}`, 'info');

            if (response.status === 200) {
                const contentType = result.contentType.toLowerCase();

                if (contentType.includes('multipart/x-mixed-replace')) {
                    result.success = true;
                    result.type = 'mjpeg-stream';
                    this.log(`  ✓ MJPEG流可用`, 'success');
                } else if (contentType.includes('image/')) {
                    result.success = true;
                    result.type = 'image';
                    this.log(`  ✓ 单帧图像可用`, 'success');
                } else if (contentType.includes('text/html')) {
                    // HTML页面，可能需要检查其他端点
                    this.log(`  收到HTML页面，可能是主页`, 'warning');
                }
            }
        } catch (error) {
            result.error = error.message;
            this.log(`  ✗ 失败: ${error.message}`, 'error');
        }

        return result;
    }

    /**
     * 连接到ESP32摄像头
     */
    async connect(url) {
        if (this.state.isConnecting) {
            this.log('正在连接中，请稍候...', 'warning');
            return false;
        }

        this.state.isConnecting = true;
        this.state.currentUrl = url;

        this.updateStatus('connecting');
        if (this.callbacks.onConnecting) {
            this.callbacks.onConnecting(url);
        }

        // 先诊断
        const diagnosis = await this.diagnose(url);

        if (!diagnosis.success || !diagnosis.workingEndpoint) {
            this.state.isConnecting = false;
            this.updateStatus('disconnected');
            if (this.callbacks.onError) {
                this.callbacks.onError('未找到可用的视频流端点，请检查网络连接和ESP32设备');
            }
            return false;
        }

        const workingEndpoint = diagnosis.workingEndpoint;

        this.state.isConnected = true;
        this.state.isPlaying = true;
        this.state.isConnecting = false;

        this.updateStatus('connected');
        if (this.callbacks.onConnected) {
            this.callbacks.onConnected(workingEndpoint.url);
        }

        // 开始流传输
        if (workingEndpoint.type === 'mjpeg-stream') {
            this.startMJPEGStream(workingEndpoint.url);
        } else {
            this.startImagePolling(workingEndpoint.url);
        }

        return true;
    }

    /**
     * 启动MJPEG流 - 优化版：使用video标签实现真正的实时传输
     */
    startMJPEGStream(url) {
        this.log('启动MJPEG实时流: ' + url, 'info');

        if (this.videoElement) {
            this.videoElement.style.display = 'block';
            this.videoElement.src = url;
            this.videoElement.autoplay = true;
            this.videoElement.playsInline = true;
            this.videoElement.muted = true;

            const video = this.videoElement;

            video.onloadedmetadata = () => {
                this.log('MJPEG流已加载，分辨率: ' + video.videoWidth + 'x' + video.videoHeight, 'success');

                // 设置canvas尺寸用于检测
                if (this.canvasElement) {
                    this.canvasElement.width = video.videoWidth || 640;
                    this.canvasElement.height = video.videoHeight || 480;
                }
            };

            video.onplay = () => {
                this.log('MJPEG流开始播放', 'success');
                this.state.isPlaying = true;

                // 开始定时捕获帧用于检测
                this.startFrameCaptureForDetection();
            };

            video.onerror = () => {
                this.log('MJPEG流加载失败，降级到轮询模式', 'error');
                this.startImagePolling(url);
            };
        }

        if (this.canvasElement) {
            this.canvasElement.style.display = 'none';
        }
    }

    /**
     * 启动图像轮询
     */
    startImagePolling(url) {
        this.log('启动图像轮询: ' + url, 'info');

        if (this.canvasElement) {
            this.canvasElement.style.display = 'block';
        }
        if (this.videoElement) {
            this.videoElement.style.display = 'none';
        }

        this.loadPollingFrame(url);
    }

    /**
     * 启动帧捕获用于检测（从video标签捕获到canvas）
     */
    startFrameCaptureForDetection() {
        if (this.state.captureIntervalId) {
            clearInterval(this.state.captureIntervalId);
        }

        // 每秒捕获1帧用于检测（与DETECTION_INTERVAL保持一致）
        this.state.captureIntervalId = setInterval(() => {
            if (!this.state.isConnected || !this.state.isPlaying) return;

            if (this.videoElement && this.canvasElement && this.canvasContext) {
                try {
                    const video = this.videoElement;
                    if (video.readyState >= 2) { // HAVE_CURRENT_DATA
                        this.canvasElement.width = video.videoWidth || 640;
                        this.canvasElement.height = video.videoHeight || 480;

                        this.canvasContext.drawImage(video, 0, 0,
                            this.canvasElement.width,
                            this.canvasElement.height);

                        if (this.callbacks.onFrameReceived) {
                            this.callbacks.onFrameReceived(this.canvasElement);
                        }
                    }
                } catch (error) {
                    this.log('帧捕获失败: ' + error.message, 'error');
                }
            }
        }, 1000); // 1000ms = 1秒1帧，与检测频率保持一致

        this.log('帧捕获已启动（1帧/秒）', 'info');
    }

    /**
     * 加载单帧（轮询方式）
     */
    async loadPollingFrame(url) {
        if (!this.state.isConnected || !this.state.isPlaying) {
            return;
        }

        const img = new Image();
        img.crossOrigin = 'anonymous';

        img.onload = () => {
            this.drawFrame(img);
            if (this.callbacks.onFrameReceived) {
                this.callbacks.onFrameReceived(img);
            }

            if (this.state.isPlaying) {
                setTimeout(() => {
                    this.loadPollingFrame(url);
                }, this.config.frameInterval);
            }
        };

        img.onerror = () => {
            this.log('帧加载失败，重试...', 'warning');
            if (this.state.isPlaying) {
                setTimeout(() => {
                    this.loadPollingFrame(url);
                }, 1000);
            }
        };

        img.src = url + '?' + new Date().getTime();
    }

    /**
     * 绘制帧到canvas
     */
    drawFrame(img) {
        if (!this.canvasElement || !this.canvasContext) {
            return;
        }

        if (img.width !== this.canvasElement.width || img.height !== this.canvasElement.height) {
            this.canvasElement.width = img.width || 640;
            this.canvasElement.height = img.height || 480;
        }

        this.canvasContext.clearRect(0, 0, this.canvasElement.width, this.canvasElement.height);
        this.canvasContext.drawImage(img, 0, 0, this.canvasElement.width, this.canvasElement.height);
    }

    /**
     * 断开连接
     */
    disconnect() {
        this.log('断开连接', 'info');

        this.state.isPlaying = false;
        this.state.isConnected = false;

        if (this.state.imgElement) {
            this.state.imgElement.src = '';
            this.state.imgElement = null;
        }

        if (this.state.streamIntervalId) {
            clearInterval(this.state.streamIntervalId);
            this.state.streamIntervalId = null;
        }

        if (this.state.captureIntervalId) {
            clearInterval(this.state.captureIntervalId);
            this.state.captureIntervalId = null;
        }

        // 停止video播放
        if (this.videoElement) {
            this.videoElement.src = '';
            this.videoElement.style.display = 'none';
        }

        // 清空canvas
        if (this.canvasElement && this.canvasContext) {
            this.canvasContext.fillStyle = '#000';
            this.canvasContext.fillRect(0, 0, this.canvasElement.width, this.canvasElement.height);
        }

        this.updateStatus('disconnected');
        if (this.callbacks.onDisconnected) {
            this.callbacks.onDisconnected();
        }
    }

    /**
     * 更新状态
     */
    updateStatus(status) {
        if (this.callbacks.onStatusChange) {
            this.callbacks.onStatusChange(status);
        }
    }

    /**
     * 获取状态
     */
    getStatus() {
        return {
            isConnecting: this.state.isConnecting,
            isConnected: this.state.isConnected,
            isPlaying: this.state.isPlaying,
            currentUrl: this.state.currentUrl
        };
    }
}

window.Esp32CameraManager = Esp32CameraManager;