// 全局变量
let currentCamera = 'local';
let videoStream = null;
let detectionInterval = null;
let espCameraUrl = 'http://192.168.241.121/';
const DETECTION_INTERVAL = 1000;
let espCameraManager = null;
let speechSynthesis = window.speechSynthesis;
let currentUtterance = null;
let speechQueue = [];
let isSpeaking = false;
let detectionTimestamps = [];
let isTestingDetectionRate = false;
let currentLocation = null;
let currentLocationMethod = null; // 存储定位方式：'gps' 或 'ip'

// IP地址配置管理
const IP_CONFIG_KEY = 'esp32_ip_history';
const MAX_HISTORY_ITEMS = 10;

function validateIpAddress(input) {
    let ip = input.trim();
    
    if (!ip) {
        return { isValid: false, error: 'IP地址不能为空', formattedIp: null };
    }
    
    if (ip.length > 255) {
        return { isValid: false, error: '输入过长，请检查', formattedIp: null };
    }
    
    let hasProtocol = ip.startsWith('http://') || ip.startsWith('https://');
    let cleanIp = ip;
    
    if (hasProtocol) {
        try {
            const urlObj = new URL(ip);
            cleanIp = urlObj.hostname;
        } catch (e) {
            return { isValid: false, error: 'URL格式无效', formattedIp: null };
        }
    }
    
    const ipv4Pattern = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/;
    const ipv6Pattern = /^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$|^::$/;
    const hostnamePattern = /^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$/;
    
    let isValidFormat = false;
    
    if (ipv4Pattern.test(cleanIp)) {
        const parts = cleanIp.split('.');
        isValidFormat = parts.every(part => {
            const num = parseInt(part, 10);
            return num >= 0 && num <= 255 && part === String(num);
        });
        
        if (!isValidFormat) {
            return { isValid: false, error: 'IPv4地址格式无效（每个段必须在0-255之间）', formattedIp: null };
        }
    } else if (ipv6Pattern.test(cleanIp)) {
        isValidFormat = true;
    } else if (hostnamePattern.test(cleanIp) && cleanIp.length <= 253) {
        isValidFormat = true;
    } else {
        return { 
            isValid: false, 
            error: '请输入有效的IP地址或域名（例如：192.168.1.100 或 esp32-camera.local）', 
            formattedIp: null 
        };
    }
    
    let formattedIp = ip;
    if (!hasProtocol) {
        formattedIp = `http://${ip}/`;
    } else if (!ip.endsWith('/')) {
        formattedIp = `${ip}/`;
    }
    
    return { isValid: true, error: null, formattedIp: formattedIp, cleanIp: cleanIp };
}

function getIpHistory() {
    try {
        const history = localStorage.getItem(IP_CONFIG_KEY);
        return history ? JSON.parse(history) : [];
    } catch (e) {
        console.error('读取IP历史记录失败:', e);
        return [];
    }
}

function saveIpToHistory(ip) {
    if (!ip || !ip.trim()) return;
    
    let history = getIpHistory();
    
    history = history.filter(item => item !== ip);
    
    history.unshift(ip);
    
    if (history.length > MAX_HISTORY_ITEMS) {
        history = history.slice(0, MAX_HISTORY_ITEMS);
    }
    
    try {
        localStorage.setItem(IP_CONFIG_KEY, JSON.stringify(history));
    } catch (e) {
        console.error('保存IP历史记录失败:', e);
    }
}

function clearIpHistory() {
    try {
        localStorage.removeItem(IP_CONFIG_KEY);
        renderIpHistoryList();
        showFeedback('info', '历史记录已清空');
    } catch (e) {
        console.error('清空IP历史记录失败:', e);
    }
}

function renderIpHistoryList() {
    const historyList = document.getElementById('ipHistoryList');
    if (!historyList) return;
    
    const history = getIpHistory();
    
    if (history.length === 0) {
        historyList.innerHTML = `
            <li><a class="dropdown-item text-muted text-center small" href="#">
                <i class="bi bi-clock"></i> 暂无历史记录
            </a></li>
        `;
        return;
    }
    
    historyList.innerHTML = history.map((ip, index) => `
        <li>
            <a class="dropdown-item" href="#" data-ip="${escapeHtml(ip)}" onclick="selectIpFromHistory('${escapeHtml(ip)}'); return false;">
                <i class="bi ${index === 0 ? 'bi-clock-fill text-primary' : 'bi-clock'}"></i>
                <span class="${index === 0 ? 'fw-bold' : ''}">${escapeHtml(ip)}</span>
                ${index === 0 ? '<span class="badge bg-primary ms-2">最近</span>' : ''}
            </a>
        </li>
    `).join('');
}

function selectIpFromHistory(ip) {
    const input = document.getElementById('espCameraUrl');
    if (input) {
        input.value = ip;
        espCameraUrl = ip;
        updateCurrentUrlDisplay(ip);
        validateAndShowFeedback(ip);
        
        const dropdownBtn = document.getElementById('historyDropdownBtn');
        if (dropdownBtn) {
            const dropdown = bootstrap.Dropdown.getInstance(dropdownBtn);
            if (dropdown) {
                dropdown.hide();
            }
        }
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function updateCurrentUrlDisplay(url) {
    const displayEl = document.getElementById('currentUrlDisplay');
    if (!displayEl) return;
    
    if (url) {
        displayEl.textContent = url;
    } else {
        displayEl.textContent = espCameraUrl || '未配置';
    }
}

// 更新ESP32下位机通信状态
function updateEsp32CommStatus(status, message = '') {
    const statusEl = document.getElementById('esp32CommStatus');
    if (!statusEl) return;

    statusEl.className = 'badge';
    
    switch (status) {
        case 'success':
            statusEl.classList.add('bg-success');
            statusEl.textContent = '✓ 已发送';
            if (message) {
                statusEl.title = message;
            }
            // 3秒后恢复为"已连接"
            setTimeout(() => {
                if (currentCamera === 'esp32') {
                    statusEl.className = 'badge bg-primary';
                    statusEl.textContent = '已连接';
                }
            }, 3000);
            break;
        case 'error':
            statusEl.classList.add('bg-danger');
            statusEl.textContent = '✗ 失败';
            statusEl.title = message || '发送失败';
            break;
        case 'sending':
            statusEl.classList.add('bg-warning');
            statusEl.textContent = '发送中...';
            break;
        case 'connected':
            statusEl.classList.add('bg-primary');
            statusEl.textContent = '已连接';
            statusEl.title = '';
            break;
        default:
            statusEl.classList.add('bg-secondary');
            statusEl.textContent = '未连接';
            statusEl.title = '';
    }
}

function showValidationFeedback(message, type) {
    const feedbackEl = document.getElementById('ipValidationFeedback');
    if (!feedbackEl) return;
    
    if (!message) {
        feedbackEl.innerHTML = '';
        return;
    }
    
    const iconClass = type === 'success' ? 'bi-check-circle-fill text-success' :
                      type === 'error' ? 'bi-x-circle-fill text-danger' :
                      type === 'warning' ? 'bi-exclamation-circle-fill text-warning' :
                      'bi-info-circle-fill text-info';
    
    feedbackEl.innerHTML = `<i class="bi ${iconClass}"></i> ${message}`;
}

function showErrorAlert(message) {
    const alertEl = document.getElementById('ipErrorAlert');
    const messageEl = document.getElementById('ipErrorMessage');
    const successEl = document.getElementById('ipSuccessAlert');
    
    if (alertEl && messageEl) {
        messageEl.textContent = message;
        alertEl.classList.remove('d-none');
    }
    
    if (successEl) {
        successEl.classList.add('d-none');
    }
}

function showSuccessAlert(message) {
    const alertEl = document.getElementById('ipSuccessAlert');
    const messageEl = document.getElementById('ipSuccessMessage');
    const errorEl = document.getElementById('ipErrorAlert');
    
    if (alertEl && messageEl) {
        messageEl.textContent = message;
        alertEl.classList.remove('d-none');
    }
    
    if (errorEl) {
        errorEl.classList.add('d-none');
    }
    
    setTimeout(() => {
        if (alertEl) {
            alertEl.classList.add('d-none');
        }
    }, 3000);
}

function hideAllAlerts() {
    const errorEl = document.getElementById('ipErrorAlert');
    const successEl = document.getElementById('ipSuccessAlert');
    
    if (errorEl) errorEl.classList.add('d-none');
    if (successEl) successEl.classList.add('d-none');
}

function updateConnectionBadge(status) {
    const badge = document.getElementById('connectionStatusBadge');
    if (!badge) return;
    
    badge.className = 'badge';
    
    switch (status) {
        case 'configured':
            badge.classList.add('bg-success');
            badge.textContent = '已配置';
            break;
        case 'connecting':
            badge.classList.add('bg-warning');
            badge.textContent = '连接中...';
            break;
        case 'connected':
            badge.classList.add('bg-primary');
            badge.textContent = '已连接';
            break;
        case 'error':
            badge.classList.add('bg-danger');
            badge.textContent = '错误';
            break;
        default:
            badge.classList.add('bg-secondary');
            badge.textContent = '未配置';
    }
}

function updateLastConnectedInfo(url) {
    const infoEl = document.getElementById('lastConnectedInfo');
    if (!infoEl) return;
    
    if (url) {
        const now = new Date();
        const timeStr = now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
        infoEl.innerHTML = `<i class="bi bi-info-circle"></i> 上次配置：${timeStr} - ${escapeHtml(url)}`;
    } else {
        infoEl.innerHTML = `<i class="bi bi-info-circle"></i> 上次连接：未连接`;
    }
}

function validateAndShowFeedback(inputValue) {
    hideAllAlerts();
    
    if (!inputValue) {
        showValidationFeedback('', '');
        updateConnectionBadge('default');
        return null;
    }
    
    const validation = validateIpAddress(inputValue);
    
    if (validation.isValid) {
        showValidationFeedback(`格式有效: ${validation.cleanIp}`, 'success');
        updateConnectionBadge('configured');
    } else {
        showValidationFeedback(validation.error, 'error');
        updateConnectionBadge('error');
    }
    
    return validation;
}

async function applyIpConfiguration() {
    const input = document.getElementById('espCameraUrl');
    if (!input) return;
    
    const inputValue = input.value.trim();
    hideAllAlerts();
    
    if (!inputValue) {
        showErrorAlert('请输入ESP32摄像头的IP地址或域名');
        input.focus();
        return false;
    }
    
    const validation = validateIpAddress(inputValue);
    
    if (!validation.isValid) {
        showErrorAlert(validation.error);
        showValidationFeedback(validation.error, 'error');
        updateConnectionBadge('error');
        input.focus();
        input.select();
        return false;
    }
    
    const applyBtn = document.getElementById('applyIpConfigBtn');
    if (applyBtn) {
        applyBtn.disabled = true;
        applyBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>应用中...';
    }
    
    updateConnectionBadge('connecting');
    showValidationFeedback('正在验证连接...', 'warning');
    
    await new Promise(resolve => setTimeout(resolve, 300));
    
    espCameraUrl = validation.formattedIp;
    
    saveIpToHistory(validation.formattedIp);
    renderIpHistoryList();
    
    localStorage.setItem('esp32_last_url', validation.formattedIp);
    
    input.value = validation.formattedIp;
    
    updateCurrentUrlDisplay(validation.formattedIp);
    updateConnectionBadge('configured');
    updateLastConnectedInfo(validation.formattedIp);
    
    showValidationFeedback(`已应用: ${validation.cleanIp}`, 'success');
    showSuccessAlert(`IP地址配置成功！摄像头地址设置为: ${validation.cleanIp}`);
    
    if (applyBtn) {
        applyBtn.disabled = false;
        applyBtn.innerHTML = '<i class="bi bi-check-lg"></i> 应用';
    }
    
    addLogEntry(`IP地址已更新为: ${validation.formattedIp}`, 'success');
    
    return true;
}

function initIpConfigManager() {
    const input = document.getElementById('espCameraUrl');
    const applyBtn = document.getElementById('applyIpConfigBtn');
    const clearHistoryBtn = document.getElementById('clearHistoryBtn');
    
    if (input) {
        let debounceTimer;
        input.addEventListener('input', function(e) {
            clearTimeout(debounceTimer);
            espCameraUrl = e.target.value;
            updateCurrentUrlDisplay(e.target.value);
            debounceTimer = setTimeout(() => {
                validateAndShowFeedback(e.target.value);
            }, 500);
        });
        
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                applyIpConfiguration();
            }
        });
        
        input.addEventListener('focus', function() {
            renderIpHistoryList();
        });
    }
    
    if (applyBtn) {
        applyBtn.addEventListener('click', function() {
            applyIpConfiguration();
        });
    }
    
    if (clearHistoryBtn) {
        clearHistoryBtn.addEventListener('click', function() {
            if (confirm('确定要清空所有IP历史记录吗？')) {
                clearIpHistory();
            }
        });
    }
    
    renderIpHistoryList();
    
    const savedUrl = localStorage.getItem('esp32_last_url');
    if (savedUrl) {
        if (input) {
            input.value = savedUrl;
        }
        espCameraUrl = savedUrl;
        updateCurrentUrlDisplay(savedUrl);
        validateAndShowFeedback(savedUrl);
    } else {
        updateCurrentUrlDisplay(espCameraUrl);
        validateAndShowFeedback(input ? input.value : '');
    }
}

// 初始化ESP32摄像头管理器
function initEsp32CameraManager() {
    if (typeof Esp32CameraManager !== 'undefined') {
        espCameraManager = new Esp32CameraManager();

        const canvasElement = document.getElementById('canvasElement');
        const videoElement = document.getElementById('videoElement');
        const resultContainer = document.getElementById('resultContainer');

        espCameraManager.init({
            canvasElement: canvasElement,
            videoElement: videoElement,
            onConnecting: function (url) {
                updateConnectionStatus('connecting', url);
            },
            onConnected: function (url) {
                updateConnectionStatus('connected', url);
                showVideoOverlay(false);
            },
            onDisconnected: function () {
                updateConnectionStatus('disconnected', null);
                showVideoOverlay(true);
            },
            onFrameReceived: function (img) {
                // 这里不需要更新统计，因为简化版没有统计
            },
            onError: function (error) {
                addLogEntry(error, 'error');
            },
            onStatusChange: function (status) {
                console.log('[ESP32] 状态变化:', status);
            },
            onLog: function (message, type) {
                addLogEntry(message, type);
            }
        });
    }
}

// 更新连接状态显示
function updateConnectionStatus(status, url) {
    const connectionInfo = document.getElementById('connectionInfo');
    const connectionStatusIcon = document.getElementById('connectionStatusIcon');
    const connectionStatusText = document.getElementById('connectionStatusText');
    const currentUrlText = document.getElementById('currentUrlText');

    if (!connectionInfo) return;

    connectionInfo.style.display = 'block';

    connectionStatusIcon.className = 'bi bi-circle-fill connection-status';

    switch (status) {
        case 'connecting':
            connectionStatusIcon.classList.add('status-connecting');
            connectionStatusText.textContent = '连接中...';
            break;
        case 'connected':
            connectionStatusIcon.classList.add('status-connected');
            connectionStatusText.textContent = '已连接';
            break;
        case 'disconnected':
            connectionStatusIcon.classList.add('status-disconnected');
            connectionStatusText.textContent = '未连接';
            break;
    }

    if (url) {
        currentUrlText.textContent = url;
    }
}

// 更新重试计数显示
function updateRetryCount(retryCount, maxRetries) {
    const retryCountText = document.getElementById('retryCountText');
    if (retryCountText) {
        retryCountText.textContent = `${retryCount} / ${maxRetries}`;
    }
}

// 更新摄像头统计信息
function updateCameraStats() {
    if (!espCameraManager) return;

    const status = espCameraManager.getStatus();

    const totalFramesText = document.getElementById('totalFramesText');
    const frameRateText = document.getElementById('frameRateText');
    const lastFrameTimeText = document.getElementById('lastFrameTimeText');

    if (totalFramesText) {
        totalFramesText.textContent = status.totalFrames;
    }

    if (frameRateText) {
        frameRateText.textContent = status.frameRate.toFixed(2);
    }

    if (lastFrameTimeText && status.lastFrameTime) {
        const now = new Date();
        lastFrameTimeText.textContent = now.toLocaleTimeString();
    }
}

// 显示/隐藏视频覆盖层
function showVideoOverlay(show) {
    const videoOverlay = document.getElementById('videoOverlay');
    if (videoOverlay) {
        videoOverlay.style.display = show ? 'flex' : 'none';
    }
}

// 添加日志条目
function addLogEntry(message, type = 'info') {
    const logContainer = document.getElementById('logContainer');
    if (!logContainer) return;

    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;

    const timestamp = new Date().toLocaleTimeString();
    entry.textContent = `[${timestamp}] ${message}`;

    logContainer.appendChild(entry);
    logContainer.scrollTop = logContainer.scrollHeight;
}

// 清空日志
function clearLogs() {
    const logContainer = document.getElementById('logContainer');
    if (!logContainer) return;

    logContainer.innerHTML = '<div class="log-entry">日志已清空</div>';
}

// 测试连接
async function testEsp32Connection() {
    const urlInput = document.getElementById('espCameraUrl');
    const urlValidationIcon = document.getElementById('urlValidationIcon');

    if (!urlInput || !espCameraManager) return;

    const url = urlInput.value.trim();
    addLogEntry(`正在测试连接: ${url}`, 'info');

    const validation = espCameraManager.validateUrl(url);

    if (!validation.isValid) {
        if (urlValidationIcon) {
            urlValidationIcon.innerHTML = '<i class="bi bi-x-circle text-danger"></i>';
        }
        addLogEntry(`URL格式无效: ${validation.error}`, 'error');
        return;
    }

    if (urlValidationIcon) {
        urlValidationIcon.innerHTML = '<i class="bi bi-hourglass-split text-warning"></i>';
    }

    const result = await espCameraManager.testConnection(validation.formattedUrl);

    if (result.success) {
        if (urlValidationIcon) {
            urlValidationIcon.innerHTML = '<i class="bi bi-check-circle text-success"></i>';
        }
        addLogEntry(`连接成功! 分辨率: ${result.width}x${result.height}`, 'success');
    } else {
        if (urlValidationIcon) {
            urlValidationIcon.innerHTML = '<i class="bi bi-x-circle text-danger"></i>';
        }
        addLogEntry(`连接失败: ${result.error}`, 'error');
    }
}

// 运行诊断
async function runDiagnostics() {
    clearLogs();
    addLogEntry('开始运行诊断...', 'info');

    const urlInput = document.getElementById('espCameraUrl');
    if (!urlInput || !espCameraManager) {
        addLogEntry('ESP32摄像头管理器未初始化', 'error');
        return;
    }

    const url = urlInput.value.trim();
    addLogEntry(`目标地址: ${url}`, 'info');

    addLogEntry('步骤1: 验证URL格式...', 'info');
    const validation = espCameraManager.validateUrl(url);

    if (!validation.isValid) {
        addLogEntry(`URL格式无效: ${validation.error}`, 'error');
        return;
    }
    addLogEntry('URL格式有效', 'success');

    addLogEntry('步骤2: 测试网络连接...', 'info');
    const buildResult = espCameraManager.buildStreamUrl(url);

    if (!buildResult.success) {
        addLogEntry(`URL构建失败: ${buildResult.error}`, 'error');
        return;
    }

    addLogEntry(`检测到的端点: ${buildResult.detectedEndpoints.length}个`, 'info');
    buildResult.detectedEndpoints.forEach((endpoint, index) => {
        addLogEntry(`  ${index + 1}. ${endpoint}`, 'info');
    });

    addLogEntry('步骤3: 尝试连接各个端点...', 'info');

    for (const testUrl of buildResult.detectedEndpoints) {
        addLogEntry(`正在测试: ${testUrl}`, 'info');
        const testResult = await espCameraManager.testConnection(testUrl);

        if (testResult.success) {
            addLogEntry(`✓ 成功连接! 分辨率: ${testResult.width}x${testResult.height}`, 'success');
            addLogEntry('诊断完成 - 找到可用端点', 'success');
            return;
        } else {
            addLogEntry(`✗ 失败: ${testResult.error}`, 'error');
        }
    }

    addLogEntry('诊断完成 - 所有端点均无法连接', 'error');
    addLogEntry('请检查: 1. ESP32设备是否开启 2. IP地址是否正确 3. 网络是否连通', 'warning');
}

// 截图功能
function takeSnapshot() {
    const canvasElement = document.getElementById('canvasElement');
    if (!canvasElement) return;

    try {
        const dataUrl = canvasElement.toDataURL('image/jpeg', 0.9);
        const link = document.createElement('a');
        link.download = `esp32_capture_${Date.now()}.jpg`;
        link.href = dataUrl;
        link.click();
        addLogEntry('截图已保存', 'success');
    } catch (error) {
        addLogEntry(`截图失败: ${error.message}`, 'error');
    }
}

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function () {
    // 初始化哈希路由
    initHashRouting();

    // 初始化滚动动画
    initScrollAnimation();

    // 初始化表单事件监听
    initFormEventListeners();

    // 初始化按钮事件监听
    initButtonEventListeners();

    // 初始化视频流功能
    initVideoStream();

    // 初始化语音播报功能
    initSpeechFunctions();

    // 初始化ESP32摄像头管理器
    initEsp32CameraManager();

    // 初始化IP配置管理器
    initIpConfigManager();

    // 初始化ESP32特定按钮事件
    initEsp32ButtonEvents();
});

// 初始化ESP32特定按钮事件
function initEsp32ButtonEvents() {
    // 诊断连接按钮
    const diagnoseConnectionBtn = document.getElementById('diagnoseConnectionBtn');
    if (diagnoseConnectionBtn) {
        diagnoseConnectionBtn.addEventListener('click', async function () {
            const urlInput = document.getElementById('espCameraUrl');
            if (!urlInput || !espCameraManager) return;

            clearLogs();
            const url = urlInput.value.trim();
            addLogEntry('开始诊断ESP32摄像头...', 'info');

            const result = await espCameraManager.diagnose(url);

            if (result.success) {
                addLogEntry('诊断成功！找到可用端点: ' + result.workingEndpoint.url, 'success');
            } else {
                addLogEntry('诊断失败，未找到可用端点', 'error');
            }
        });
    }

    // 直接连接按钮
    const directConnectBtn = document.getElementById('directConnectBtn');
    if (directConnectBtn) {
        directConnectBtn.addEventListener('click', async function () {
            const urlInput = document.getElementById('espCameraUrl');
            if (!urlInput || !espCameraManager) return;

            const url = urlInput.value.trim();
            addLogEntry('尝试直接连接...', 'info');

            const connected = await espCameraManager.connect(url);

            if (connected) {
                addLogEntry('连接成功！', 'success');
            } else {
                addLogEntry('连接失败，请先运行诊断', 'error');
            }
        });
    }

    // 清空日志按钮
    const clearLogsBtn = document.getElementById('clearLogsBtn');
    if (clearLogsBtn) {
        clearLogsBtn.addEventListener('click', clearLogs);
    }

    // 截图按钮
    const snapshotBtn = document.getElementById('snapshotBtn');
    if (snapshotBtn) {
        snapshotBtn.addEventListener('click', takeSnapshot);
    }

    // ESP32 URL输入框 - 实时验证（已移至initIpConfigManager）
    // 保留此处的日志记录功能
    const espCameraUrlInput = document.getElementById('espCameraUrl');
    if (espCameraUrlInput) {
        espCameraUrlInput.addEventListener('change', function (e) {
            espCameraUrl = e.target.value;
            console.log('[ESP32] URL已更新:', espCameraUrl);
        });
    }
}

// 防抖函数
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 初始化滚动动画
function initScrollAnimation() {
    const sections = document.querySelectorAll('section');

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, {
        threshold: 0.1
    });

    sections.forEach(section => {
        observer.observe(section);
    });
}

// 初始化哈希路由
function initHashRouting() {
    // 监听哈希变化
    window.addEventListener('hashchange', handleHashChange);

    // 初始加载时处理当前哈希
    handleHashChange();

    // 处理导航链接点击
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', function (e) {
            // 移除所有活动状态
            navLinks.forEach(l => l.classList.remove('active'));
            // 添加当前链接的活动状态
            this.classList.add('active');
        });
    });
}

// 处理哈希变化
function handleHashChange() {
    const hash = window.location.hash || '#home';

    // 隐藏所有section
    const sections = document.querySelectorAll('section');
    sections.forEach(section => {
        section.style.display = 'none';
    });

    // 显示当前哈希对应的section
    const targetSection = document.querySelector(hash);
    if (targetSection) {
        targetSection.style.display = 'block';

        // 更新导航栏活动状态
        const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === hash) {
                link.classList.add('active');
            }
        });

        // 滚动到顶部
        window.scrollTo(0, 0);

        // 触发特定页面的初始化
        initPageSpecificFeatures(hash);
    } else {
        // 如果哈希不存在，默认显示首页
        const homeSection = document.querySelector('#home');
        if (homeSection) {
            homeSection.style.display = 'block';
            const homeLink = document.querySelector('.navbar-nav .nav-link[href="#home"]');
            if (homeLink) {
                homeLink.classList.add('active');
            }
            initPageSpecificFeatures('#home');
        }
    }
}

// 初始化页面特定功能
function initPageSpecificFeatures(hash) {
    switch (hash) {
        case '#home':
            // 首页特定初始化
            console.log('加载首页');
            break;
        case '#detect':
            // 目标检测页面特定初始化
            console.log('加载目标检测页面');
            // 可以在这里重新初始化视频流等
            break;
        case '#location':
            // 位置查询页面特定初始化
            console.log('加载位置查询页面');
            break;
        case '#weather':
            // 天气查询页面特定初始化
            console.log('加载天气查询页面');
            break;
        case '#emergency':
            // 紧急求助页面特定初始化
            console.log('加载紧急求助页面');
            break;
        case '#ask':
            // 智能问答页面特定初始化
            console.log('加载智能问答页面');
            // 可以在这里重新聚焦到输入框
            const questionInput = document.getElementById('questionInput');
            if (questionInput) {
                questionInput.focus();
            }
            break;
    }
}

// 程序化导航到指定页面
function navigateTo(hash) {
    window.location.hash = hash;
}

// 初始化表单事件监听
function initFormEventListeners() {
    // 目标检测表单
    const detectForm = document.getElementById('detectForm');
    if (detectForm) {
        detectForm.addEventListener('submit', handleDetectFormSubmit);
    }

    // 智能问答表单
    const askForm = document.getElementById('askForm');
    if (askForm) {
        askForm.addEventListener('submit', handleAskFormSubmit);
    }
}

// 初始化按钮事件监听
function initButtonEventListeners() {
    // 获取位置按钮
    const getLocationBtn = document.getElementById('getLocationBtn');
    if (getLocationBtn) {
        getLocationBtn.addEventListener('click', handleGetLocation);
    }

    // 紧急求助按钮
    const emergencyBtn = document.getElementById('emergencyBtn');
    if (emergencyBtn) {
        emergencyBtn.addEventListener('click', handleEmergency);
    }

    // 天气查询按钮
    const getWeatherBtn = document.getElementById('getWeatherBtn');
    if (getWeatherBtn) {
        getWeatherBtn.addEventListener('click', handleGetWeather);
    }

    // 按城市查询天气按钮
    const getWeatherByCityBtn = document.getElementById('getWeatherByCityBtn');
    if (getWeatherByCityBtn) {
        getWeatherByCityBtn.addEventListener('click', handleGetWeatherByCity);
    }

    // 识别速率测试按钮
    const testDetectionRateBtn = document.getElementById('testDetectionRateBtn');
    if (testDetectionRateBtn) {
        testDetectionRateBtn.addEventListener('click', handleTestDetectionRate);
    }

    // 重置识别速率测试按钮
    const resetDetectionRateBtn = document.getElementById('resetDetectionRateBtn');
    if (resetDetectionRateBtn) {
        resetDetectionRateBtn.addEventListener('click', handleResetDetectionRate);
    }
}

// 初始化语音播报功能
function initSpeechFunctions() {
    // 测试语音按钮
    const testSpeechBtn = document.getElementById('testSpeechBtn');
    if (testSpeechBtn) {
        testSpeechBtn.addEventListener('click', handleTestSpeech);
    }

    // 扬声器设置按钮
    const speakerGuideBtn = document.getElementById('speakerGuideBtn');
    if (speakerGuideBtn) {
        speakerGuideBtn.addEventListener('click', showSpeakerSelectionGuide);
    }

    // 清空语音队列按钮
    const clearSpeechBtn = document.getElementById('clearSpeechBtn');
    if (clearSpeechBtn) {
        clearSpeechBtn.addEventListener('click', clearSpeechQueue);
    }

    // 检查语音合成API支持
    checkSpeechSynthesisSupport();

    // 添加语音合成事件监听器
    addSpeechSynthesisListeners();
}

// 添加语音合成事件监听器
function addSpeechSynthesisListeners() {
    // 监听语音列表变化
    speechSynthesis.addEventListener('voiceschanged', () => {
        console.log('语音列表已更新');
        checkSpeechSynthesisSupport();
    });
}

// 检查语音合成API支持
function checkSpeechSynthesisSupport() {
    if (!('speechSynthesis' in window)) {
        showSpeechStatus('您的浏览器不支持语音合成功能，请使用Chrome、Edge或Firefox等现代浏览器');
        return false;
    }

    // 获取可用语音列表
    const voices = speechSynthesis.getVoices();
    if (voices.length === 0) {
        showSpeechStatus('未检测到可用的语音合成引擎，请检查系统语音设置');
        return false;
    }

    // 显示可用语音信息
    const chineseVoices = voices.filter(voice => voice.lang.includes('zh'));
    if (chineseVoices.length > 0) {
        showSpeechStatus(`检测到 ${chineseVoices.length} 个中文语音引擎，语音播报功能已就绪`);
    } else {
        showSpeechStatus('未检测到中文语音引擎，语音播报可能无法正常工作');
    }

    return true;
}

// 处理测试语音按钮点击
function handleTestSpeech() {
    const testTexts = [
        '语音播报功能测试，第一句话。',
        '语音播报功能测试，第二句话。',
        '语音播报功能测试，第三句话。'
    ];

    // 清空当前队列
    clearSpeechQueue();

    // 添加测试文本到队列
    testTexts.forEach(text => {
        speakText(text);
    });

    showSpeechStatus('已添加测试语音到队列，请检查扬声器是否有声音');
}

// 显示扬声器选择指南
function showSpeakerSelectionGuide() {
    const guideHtml = `
        <div class="alert alert-warning">
            <h6><i class="bi bi-speaker"></i> 扬声器选择指南</h6>
            <p>如果语音播报没有声音，请按以下步骤检查：</p>
            <ol>
                <li><strong>检查系统音量</strong>：确保电脑音量已调高且未静音</li>
                <li><strong>选择默认扬声器</strong>：
                    <ul>
                        <li>Windows：右键点击音量图标 → 打开声音设置 → 选择输出设备为 Senary Audio</li>
                        <li>Mac：系统偏好设置 → 声音 → 输出 → 选择 Senary Audio</li>
                    </ul>
                </li>
                <li><strong>浏览器权限</strong>：确保浏览器有播放音频的权限</li>
                <li><strong>测试系统语音</strong>：使用系统自带的语音合成功能测试扬声器</li>
            </ol>
            <button class="btn btn-sm btn-outline-primary" onclick="testSystemSpeech()">测试系统语音</button>
        </div>
    `;

    const resultContainer = document.getElementById('resultContainer');
    if (resultContainer) {
        resultContainer.innerHTML = guideHtml;
    }
}

// 测试系统语音合成
function testSystemSpeech() {
    if (!('speechSynthesis' in window)) {
        alert('您的浏览器不支持语音合成功能');
        return;
    }

    const testText = '这是系统语音合成测试，如果您能听到这句话，说明语音合成功能正常。';
    const utterance = new SpeechSynthesisUtterance(testText);
    utterance.lang = 'zh-CN';
    utterance.rate = 0.9;
    utterance.volume = 1;

    utterance.onstart = function () {
        showSpeechStatus('系统语音测试开始...');
    };

    utterance.onend = function () {
        showSpeechStatus('系统语音测试完成，请确认是否听到声音');
    };

    utterance.onerror = function (event) {
        showSpeechError('系统语音测试失败: ' + event.error);
    };

    speechSynthesis.speak(utterance);
}

// 初始化视频流功能
function initVideoStream() {
    // 获取DOM元素
    const localCameraBtn = document.getElementById('localCameraBtn');
    const espCameraBtn = document.getElementById('espCameraBtn');
    const espCameraUrlInput = document.getElementById('espCameraUrl');
    const startStreamBtn = document.getElementById('startStreamBtn');
    const stopStreamBtn = document.getElementById('stopStreamBtn');

    // 摄像头切换按钮事件
    if (localCameraBtn) {
        localCameraBtn.addEventListener('click', () => switchCamera('local'));
    }

    if (espCameraBtn) {
        espCameraBtn.addEventListener('click', () => switchCamera('esp'));
    }

    // ESP32摄像头地址输入事件
    if (espCameraUrlInput) {
        espCameraUrlInput.addEventListener('input', (e) => {
            espCameraUrl = e.target.value;
        });
    }

    // 开始/停止检测按钮事件
    if (startStreamBtn) {
        startStreamBtn.addEventListener('click', startDetection);
    }

    if (stopStreamBtn) {
        stopStreamBtn.addEventListener('click', stopDetection);
    }

    // 初始化默认摄像头
    startLocalCamera();
}

// 切换摄像头
function switchCamera(cameraType) {
    // 停止当前摄像头
    stopCamera();

    // 清空Canvas，显示黑色背景
    clearCanvas();

    // 更新当前摄像头类型
    currentCamera = cameraType;

    // 更新按钮状态
    const localCameraBtn = document.getElementById('localCameraBtn');
    const espCameraBtn = document.getElementById('espCameraBtn');
    const espCameraUrlInput = document.getElementById('espCameraUrl');

    if (localCameraBtn && espCameraBtn) {
        if (cameraType === 'local') {
            localCameraBtn.classList.remove('btn-secondary');
            localCameraBtn.classList.add('btn-primary');
            espCameraBtn.classList.remove('btn-primary');
            espCameraBtn.classList.add('btn-secondary');
            espCameraUrlInput.disabled = true;
        } else {
            localCameraBtn.classList.remove('btn-primary');
            localCameraBtn.classList.add('btn-secondary');
            espCameraBtn.classList.remove('btn-secondary');
            espCameraBtn.classList.add('btn-primary');
            espCameraUrlInput.disabled = false;
        }
    }

    // 启动新摄像头
    if (cameraType === 'local') {
        startLocalCamera();
    } else {
        startEspCamera();
    }
}

// 启动本地摄像头
async function startLocalCamera() {
    try {
        const videoElement = document.getElementById('videoElement');
        if (!videoElement) return;

        // 获取本地摄像头流
        videoStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false });
        videoElement.srcObject = videoStream;
        videoElement.style.display = 'block';

        // 隐藏canvas
        const canvasElement = document.getElementById('canvasElement');
        if (canvasElement) {
            canvasElement.style.display = 'none';
        }
    } catch (error) {
        console.error('启动本地摄像头失败:', error);
        alert('无法访问本地摄像头，请检查权限设置');
    }
}

// 启动ESP32摄像头
async function startEspCamera() {
    const videoElement = document.getElementById('videoElement');
    const canvasElement = document.getElementById('canvasElement');
    const resultContainer = document.getElementById('resultContainer');
    const urlInput = document.getElementById('espCameraUrl');

    if (!videoElement || !canvasElement) return;

    // 从输入框获取当前URL，而不是使用全局变量
    const currentUrl = urlInput ? urlInput.value.trim() : espCameraUrl;

    // 更新全局变量
    if (currentUrl) {
        espCameraUrl = currentUrl;
    }

    if (!espCameraManager) {
        console.error('ESP32摄像头管理器未初始化');
        if (resultContainer) {
            resultContainer.innerHTML = `
                <div class="alert alert-danger">
                    <h6><i class="bi bi-exclamation-triangle"></i> 系统错误</h6>
                    <p>ESP32摄像头管理器未初始化，请刷新页面重试</p>
                </div>
            `;
        }
        return;
    }

    videoElement.style.display = 'none';
    canvasElement.style.display = 'block';
    clearCanvas();

    if (resultContainer) {
        resultContainer.innerHTML = `
            <div class="alert alert-warning">
                <h6><i class="bi bi-wifi"></i> 正在连接ESP32摄像头...</h6>
                <p>摄像头地址: ${currentUrl}</p>
                <p class="small text-muted">请确保电脑已连接到ESP32的WiFi网络</p>
            </div>
        `;
    }

    const connected = await espCameraManager.connect(currentUrl);

    if (!connected) {
        if (resultContainer) {
            resultContainer.innerHTML = `
                <div class="alert alert-danger">
                    <h6><i class="bi bi-wifi-off"></i> ESP32摄像头连接失败</h6>
                    <p>摄像头地址: ${currentUrl}</p>
                    <p class="small">请检查:</p>
                    <ul class="small">
                        <li>ESP32设备是否已开机并连接到WiFi</li>
                        <li>电脑是否连接到ESP32的WiFi网络</li>
                        <li>摄像头地址是否正确（尝试端口81）</li>
                        <li>网络连接是否正常</li>
                    </ul>
                    <button class="btn btn-sm btn-primary mt-2" onclick="startEspCamera()">重新连接</button>
                </div>
            `;
        }
    } else {
        if (resultContainer) {
            resultContainer.innerHTML = '<p class="text-muted">ESP32摄像头已连接，点击"开始检测"进行目标检测</p>';
        }
        
        // 更新ESP32通信状态为"已连接"
        updateEsp32CommStatus('connected');
    }
}

// 语音播报函数
function speakText(text) {
    if (!text) return;

    // 将文本添加到队列
    speechQueue.push(text);

    // 如果当前没有正在播放的语音，开始播放队列
    if (!isSpeaking) {
        processSpeechQueue();
    }
}

// 发送语音播报文字到ESP32下位机
async function sendAnnouncementToEsp32(announcementText) {
    if (!announcementText || !espCameraUrl) {
        console.log('[ESP32] 跳过发送：无文本或未配置URL');
        return;
    }

    // 更新状态为"发送中"
    updateEsp32CommStatus('sending');

    // 构建发送到ESP32的API地址
    // 假设ESP32有 /api/announce 或 /announce 端点接收文本
    let espApiUrl = espCameraUrl;
    
    // 移除末尾的斜杠
    if (espApiUrl.endsWith('/')) {
        espApiUrl = espApiUrl.slice(0, -1);
    }
    
    // 尝试多个可能的端点
    const endpoints = [
        '/api/announce',
        '/announce',
        '/text',
        '/api/text',
        '/display'
    ];

    for (const endpoint of endpoints) {
        const fullUrl = espApiUrl + endpoint;
        
        try {
            console.log(`[ESP32] 发送文本到: ${fullUrl}`);
            console.log(`[ESP32] 文本内容: ${announcementText}`);

            const response = await fetch(fullUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text: announcementText,
                    timestamp: new Date().toISOString(),
                    source: 'detection'
                }),
                mode: 'cors', // 允许跨域请求
                timeout: 3000 // 3秒超时
            });

            if (response.ok) {
                const result = await response.json();
                console.log(`[ESP32] ✓ 发送成功:`, result);
                updateEsp32CommStatus('success', `已发送: ${announcementText.substring(0, 30)}...`);
                addLogEntry(`已将检测结果发送给ESP32: ${announcementText.substring(0, 50)}...`, 'success');
                return true;
            } else {
                console.warn(`[ESP32] 端点返回错误: ${response.status} - ${endpoint}`);
            }
        } catch (error) {
            console.warn(`[ESP32] 端点不可用: ${endpoint} - ${error.message}`);
            // 继续尝试下一个端点
        }
    }

    // 如果所有端点都失败，记录警告但不影响主流程
    console.warn('[ESP32] 所有端点均不可用，无法发送文本到ESP32');
    updateEsp32CommStatus('error', 'ESP32端点不可用');
    addLogEntry('ESP32下位机不可用，未能发送检测结果（不影响本地功能）', 'warning');
    return false;
}

// 处理语音播报队列
function processSpeechQueue() {
    // 如果队列为空，停止播放
    if (speechQueue.length === 0) {
        isSpeaking = false;
        return;
    }

    // 设置正在播放状态
    isSpeaking = true;

    // 从队列中取出第一个文本
    const text = speechQueue.shift();

    // 检查语音合成API支持
    if (!('speechSynthesis' in window)) {
        console.error('浏览器不支持语音合成API');
        showSpeechError('您的浏览器不支持语音合成功能，请使用Chrome、Edge或Firefox等现代浏览器');
        isSpeaking = false;
        return;
    }

    // 检查语音合成是否可用
    if (speechSynthesis.speaking) {
        console.log('语音合成正在播放中，等待完成');
        // 将文本重新放回队列开头
        speechQueue.unshift(text);
        setTimeout(() => {
            processSpeechQueue();
        }, 100);
        return;
    }

    // 创建新的语音合成实例
    currentUtterance = new SpeechSynthesisUtterance(text);

    // 设置语音属性
    currentUtterance.lang = 'zh-CN'; // 使用中文语音
    currentUtterance.rate = 0.9; // 稍微降低语速，让语音更清晰
    currentUtterance.pitch = 1; // 音调
    currentUtterance.volume = 1; // 音量

    // 语音播放开始事件
    currentUtterance.onstart = function () {
        console.log('语音播报开始:', text);
        showSpeechStatus('正在播放语音...');
    };

    // 语音播放结束事件
    currentUtterance.onend = function () {
        console.log('语音播报完成:', text);
        showSpeechStatus('语音播放完成');

        // 等待一小段时间再播放下一个语音，避免语音重叠
        setTimeout(() => {
            processSpeechQueue();
        }, 500); // 500毫秒间隔
    };

    // 语音播放错误事件
    currentUtterance.onerror = function (event) {
        console.error('语音播报失败:', text, '错误:', event.error);
        showSpeechError('语音播报失败: ' + event.error);

        // 继续播放下一个语音
        setTimeout(() => {
            processSpeechQueue();
        }, 500);
    };

    // 播放语音
    try {
        speechSynthesis.speak(currentUtterance);
        console.log('语音合成已启动');
    } catch (error) {
        console.error('语音合成启动失败:', error);
        showSpeechError('语音合成启动失败: ' + error.message);
        isSpeaking = false;
    }
}

// 显示语音播报状态
function showSpeechStatus(message) {
    const statusText = document.getElementById('speechStatusText');
    const statusElement = document.getElementById('speechStatus');
    const errorElement = document.getElementById('speechError');

    if (statusText) {
        statusText.textContent = message;
    }

    if (statusElement) {
        statusElement.className = 'small text-muted';
    }

    if (errorElement) {
        errorElement.classList.add('d-none');
    }
}

// 显示语音播报错误
function showSpeechError(message) {
    const errorText = document.getElementById('speechErrorText');
    const errorElement = document.getElementById('speechError');
    const statusElement = document.getElementById('speechStatus');

    if (errorText) {
        errorText.textContent = message;
    }

    if (errorElement) {
        errorElement.classList.remove('d-none');
    }

    if (statusElement) {
        statusElement.className = 'small text-muted';
    }
}

// 清空Canvas内容，显示黑色背景
function clearCanvas() {
    const canvasElement = document.getElementById('canvasElement');
    if (!canvasElement) return;

    const ctx = canvasElement.getContext('2d');
    if (!ctx) return;

    // 清空Canvas
    ctx.clearRect(0, 0, canvasElement.width, canvasElement.height);

    // 绘制黑色背景
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, canvasElement.width, canvasElement.height);
}

// 停止摄像头
function stopCamera() {
    // 停止检测
    stopDetection();

    // 清空Canvas
    clearCanvas();

    // 清空语音队列
    clearSpeechQueue();

    // 释放ESP32摄像头资源
    if (espCameraManager) {
        espCameraManager.disconnect();
    }
}

// 清空语音队列
function clearSpeechQueue() {
    speechQueue = [];
    if (currentUtterance) {
        speechSynthesis.cancel();
        currentUtterance = null;
    }
    isSpeaking = false;
}

// 开始实时检测
function startDetection() {
    const startStreamBtn = document.getElementById('startStreamBtn');
    const stopStreamBtn = document.getElementById('stopStreamBtn');

    if (startStreamBtn && stopStreamBtn) {
        startStreamBtn.disabled = true;
        stopStreamBtn.disabled = false;
    }

    // 每DETECTION_INTERVAL毫秒进行一次检测（默认1秒1帧）
    detectionInterval = setInterval(async () => {
        const frame = await captureFrame();
        if (frame) {
            await detectFrame(frame);

            // 记录识别时间戳，用于测试识别速率
            if (isTestingDetectionRate) {
                detectionTimestamps.push(Date.now());
                // 只保留最近10个时间戳
                if (detectionTimestamps.length > 10) {
                    detectionTimestamps.shift();
                }
            }
        }
    }, DETECTION_INTERVAL);
}

// 停止实时检测
function stopDetection() {
    const startStreamBtn = document.getElementById('startStreamBtn');
    const stopStreamBtn = document.getElementById('stopStreamBtn');

    if (startStreamBtn && stopStreamBtn) {
        startStreamBtn.disabled = false;
        stopStreamBtn.disabled = true;
    }

    if (detectionInterval) {
        clearInterval(detectionInterval);
        detectionInterval = null;
    }

    // 关闭摄像头
    if (videoStream) {
        videoStream.getTracks().forEach(track => track.stop());
        videoStream = null;
    }

    // 停止识别速率测试
    if (isTestingDetectionRate) {
        handleTestDetectionRate();
    }
}

// 处理识别速率测试按钮点击
function handleTestDetectionRate() {
    const testBtn = document.getElementById('testDetectionRateBtn');
    const resetBtn = document.getElementById('resetDetectionRateBtn');

    if (!testBtn || !resetBtn) return;

    if (isTestingDetectionRate) {
        // 停止测试
        isTestingDetectionRate = false;
        testBtn.textContent = '测试识别速率';
        testBtn.classList.remove('btn-warning');
        testBtn.classList.add('btn-info');
        resetBtn.disabled = true;

        // 计算并显示最终识别速率
        const finalRate = calculateDetectionRate();
        updateDetectionRateDisplay(finalRate, true);

        // 清空时间戳数组
        detectionTimestamps = [];
    } else {
        // 开始测试
        isTestingDetectionRate = true;
        testBtn.textContent = '停止测试';
        testBtn.classList.remove('btn-info');
        testBtn.classList.add('btn-warning');
        resetBtn.disabled = false;

        // 清空之前的时间戳
        detectionTimestamps = [];

        // 更新显示
        updateDetectionRateDisplay(0);
    }
}

// 处理重置识别速率测试按钮点击
function handleResetDetectionRate() {
    // 清空时间戳数组
    detectionTimestamps = [];

    // 更新显示
    updateDetectionRateDisplay(0);
}

// 计算识别速率
function calculateDetectionRate() {
    if (detectionTimestamps.length < 2) {
        return 0;
    }

    // 计算时间差的平均值
    let totalInterval = 0;
    for (let i = 1; i < detectionTimestamps.length; i++) {
        totalInterval += detectionTimestamps[i] - detectionTimestamps[i - 1];
    }

    const avgInterval = totalInterval / (detectionTimestamps.length - 1);
    const rate = 1000 / avgInterval; // 转换为每秒帧数

    return rate;
}

// 更新识别速率显示
function updateDetectionRateDisplay(rate, isFinal = false) {
    const resultElement = document.getElementById('detectionRateResult');
    if (!resultElement) return;

    if (isFinal) {
        resultElement.innerHTML = `识别速率：<strong>${rate.toFixed(2)} 帧/秒</strong>（测试完成）`;
        resultElement.className = 'small text-success';
    } else if (isTestingDetectionRate) {
        resultElement.innerHTML = `识别速率：<strong>${rate.toFixed(2)} 帧/秒</strong>（测试中...）`;
        resultElement.className = 'small text-info';
    } else {
        resultElement.innerHTML = '识别速率：未测试';
        resultElement.className = 'small text-muted';
    }

    // 如果正在测试，每秒更新一次
    if (isTestingDetectionRate && !isFinal) {
        setTimeout(() => {
            const currentRate = calculateDetectionRate();
            updateDetectionRateDisplay(currentRate);
        }, 1000);
    }
}

// 捕获视频帧
function captureFrame() {
    const videoElement = document.getElementById('videoElement');
    const canvasElement = document.getElementById('canvasElement');

    if (!videoElement || !canvasElement) return null;

    const ctx = canvasElement.getContext('2d');
    if (!ctx) return null;

    if (currentCamera === 'local') {
        // 从本地摄像头捕获帧
        canvasElement.width = videoElement.videoWidth;
        canvasElement.height = videoElement.videoHeight;
        ctx.drawImage(videoElement, 0, 0, canvasElement.width, canvasElement.height);
    }
    // 对于ESP32摄像头，canvas已经包含了当前帧的图像，不需要额外处理

    // 将canvas转换为Blob
    return new Promise((resolve) => {
        canvasElement.toBlob(blob => {
            resolve(blob);
        }, 'image/jpeg');
    });
}

// 对单帧图像进行检测
async function detectFrame(frame) {
    if (!frame) return;

    const resultContainer = document.getElementById('resultContainer');
    const announcementContainer = document.getElementById('announcementContainer');
    const announcementText = document.getElementById('announcementText');

    try {
        const formData = new FormData();
        formData.append('image', frame, 'frame.jpg');

        const response = await fetch('/api/detect', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.status === 'success') {
            // 显示检测结果
            let resultHtml = '<h6>检测到的目标：</h6>';

            if (data.detections.length > 0) {
                resultHtml += '<ul class="result-list">';
                data.detections.forEach((detection, index) => {
                    resultHtml += `
                        <li>
                            <strong>${index + 1}. ${detection.chinese_class}</strong>
                            <br>
                            置信度: ${detection.confidence.toFixed(2)}
                            <br>
                            位置: ${detection.position}
                        </li>
                    `;
                });
                resultHtml += '</ul>';
            } else {
                resultHtml += '<p class="text-muted">未检测到关键目标</p>';
            }

            resultContainer.innerHTML = resultHtml;

            // 显示语音播报文本
            announcementText.textContent = data.announcement;
            announcementContainer.classList.remove('d-none');

            // 播放语音播报
            speakText(data.announcement);
            
            // 发送检测结果到ESP32下位机（异步，不阻塞主流程）
            if (currentCamera === 'esp32') {
                sendAnnouncementToEsp32(data.announcement).catch(error => {
                    console.error('[ESP32] 发送失败:', error);
                });
            }
        } else {
            resultContainer.innerHTML = `<div class="alert alert-danger">检测失败：${data.message}</div>`;
        }
    } catch (error) {
        console.error('检测失败:', error);
        resultContainer.innerHTML = '<div class="alert alert-danger">检测失败：网络错误，请稍后重试</div>';
    }
}

// 处理目标检测表单提交
async function handleDetectFormSubmit(e) {
    e.preventDefault();

    const formData = new FormData(e.target);
    const resultContainer = document.getElementById('resultContainer');
    const announcementContainer = document.getElementById('announcementContainer');
    const announcementText = document.getElementById('announcementText');

    // 显示加载状态
    resultContainer.innerHTML = '<div class="text-center"><div class="loading"></div> <span class="ms-2">正在检测中...</span></div>';
    announcementContainer.classList.add('d-none');

    try {
        const response = await fetch('/api/detect', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.status === 'success') {
            // 显示检测结果
            let resultHtml = '<h6>检测到的目标：</h6>';

            if (data.detections.length > 0) {
                resultHtml += '<ul class="result-list">';
                data.detections.forEach((detection, index) => {
                    resultHtml += `
                        <li>
                            <strong>${index + 1}. ${detection.chinese_class}</strong>
                            <br>
                            置信度: ${detection.confidence.toFixed(2)}
                            <br>
                            位置: ${detection.position}
                        </li>
                    `;
                });
                resultHtml += '</ul>';
            } else {
                resultHtml += '<p class="text-muted">未检测到关键目标</p>';
            }

            resultContainer.innerHTML = resultHtml;

            // 显示语音播报文本
            announcementText.textContent = data.announcement;
            announcementContainer.classList.remove('d-none');
        } else {
            resultContainer.innerHTML = `<div class="alert alert-danger">检测失败：${data.message}</div>`;
        }
    } catch (error) {
        console.error('检测失败:', error);
        resultContainer.innerHTML = '<div class="alert alert-danger">检测失败：网络错误，请稍后重试</div>';
    }
}

// 处理获取位置按钮点击
async function handleGetLocation() {
    const getLocationBtn = document.getElementById('getLocationBtn');
    const locationResult = document.getElementById('locationResult');

    // 显示加载状态
    const originalText = getLocationBtn.innerHTML;
    getLocationBtn.innerHTML = '<div class="loading"></div> <span class="ms-2">正在获取...</span>';
    getLocationBtn.disabled = true;
    locationResult.innerHTML = '<div class="text-center"><div class="loading"></div> <span class="ms-2">正在获取位置信息...</span></div>';

    try {
        // 首先尝试使用浏览器GPS定位
        const position = await getCurrentPosition();
        if (position) {
            const { latitude, longitude } = position;
            console.log('GPS定位成功:', { latitude, longitude });

            // 使用GPS坐标获取位置信息
            const response = await fetch(`/api/location?lat=${latitude}&lon=${longitude}`);
            const data = await response.json();

            if (data.status === 'success') {
                // 保存位置信息到全局变量
                currentLocation = data.location;
                currentLocationMethod = 'gps';

                // 显示位置信息
                let locationHtml = `
                    <h6>当前位置：</h6>
                    <ul class="result-list">
                        <li>地址：${data.location.address || '未知地址'}</li>
                        <li>城市：${data.location.city || '未知'}</li>
                        <li>地区：${data.location.district || '未知'}</li>
                        <li>街道：${data.location.street || '未知'}</li>
                        <li>坐标：${data.location.lat.toFixed(6)}, ${data.location.lon.toFixed(6)}</li>
                    </ul>
                    <div class="alert alert-success mt-3">
                        <small><i class="bi bi-geo-alt"></i> 定位方式：GPS精确定位</small>
                    </div>
                    <div class="alert alert-info mt-3">
                        <h6><i class="bi bi-volume-up"></i> 语音播报：</h6>
                        <p>${data.announcement}</p>
                    </div>
                `;
                locationResult.innerHTML = locationHtml;

                // 播放语音播报
                speakText(data.announcement);
            } else {
                throw new Error(data.message);
            }
        } else {
            throw new Error('GPS定位失败');
        }
    } catch (gpsError) {
        console.warn('GPS定位失败，使用IP定位:', gpsError);

        try {
            // 回退到IP定位
            const response = await fetch('/api/location');
            const data = await response.json();

            if (data.status === 'success') {
                // 保存位置信息到全局变量
                currentLocation = {
                    city: data.location.city,
                    region: data.location.region,
                    country: data.location.country,
                    isp: data.location.isp,
                    ip: data.location.ip,
                    address: `${data.location.city || ''} ${data.location.region || ''} ${data.location.country || ''}`.trim() || '未知地址'
                };
                currentLocationMethod = 'ip';

                // 显示位置信息
                let locationHtml = `
                    <h6>当前位置：</h6>
                    <ul class="result-list">
                        <li>城市：${data.location.city || '未知'}</li>
                        <li>地区：${data.location.region || '未知'}</li>
                        <li>国家：${data.location.country || '未知'}</li>
                        <li>服务商：${data.location.isp || '未知'}</li>
                        <li>IP地址：${data.location.ip}</li>
                    </ul>
                    <div class="alert alert-warning mt-3">
                        <small><i class="bi bi-exclamation-triangle"></i> 定位方式：IP定位（精确度较低）</small>
                    </div>
                    <div class="alert alert-info mt-3">
                        <h6><i class="bi bi-volume-up"></i> 语音播报：</h6>
                        <p>${data.announcement}</p>
                    </div>
                `;
                locationResult.innerHTML = locationHtml;

                // 播放语音播报
                speakText(data.announcement);
            } else {
                locationResult.innerHTML = `<div class="alert alert-danger">获取位置失败：${data.message}</div>`;
            }
        } catch (ipError) {
            console.error('IP定位也失败:', ipError);
            locationResult.innerHTML = `
                <div class="alert alert-danger">
                    <h6><i class="bi bi-x-circle"></i> 位置获取失败</h6>
                    <p>GPS定位和IP定位都失败了，请检查：</p>
                    <ul class="mb-0">
                        <li>网络连接是否正常</li>
                        <li>是否允许浏览器获取位置权限</li>
                        <li>高德地图API密钥是否有效</li>
                    </ul>
                </div>
            `;
        }
    } finally {
        // 恢复按钮状态
        getLocationBtn.innerHTML = originalText;
        getLocationBtn.disabled = false;
    }
}

// 获取当前GPS位置
function getCurrentPosition() {
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            reject(new Error('浏览器不支持地理定位API'));
            return;
        }

        const options = {
            enableHighAccuracy: true,  // 请求高精度位置
            timeout: 10000,           // 超时时间10秒
            maximumAge: 300000        // 缓存时间5分钟
        };

        navigator.geolocation.getCurrentPosition(
            (position) => {
                resolve({
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                    accuracy: position.coords.accuracy
                });
            },
            (error) => {
                console.error('GPS定位失败:', error);
                let errorMessage = '未知定位错误';
                switch (error.code) {
                    case error.PERMISSION_DENIED:
                        errorMessage = '用户拒绝了地理定位请求，请允许浏览器访问位置信息';
                        break;
                    case error.POSITION_UNAVAILABLE:
                        errorMessage = '位置信息不可用，请检查GPS或网络连接';
                        break;
                    case error.TIMEOUT:
                        errorMessage = '定位请求超时，请稍后重试';
                        break;
                }
                reject(new Error(errorMessage));
            },
            options
        );
    });
}

// 处理紧急求助按钮点击
async function handleEmergency() {
    const emergencyBtn = document.getElementById('emergencyBtn');
    const emergencyResult = document.getElementById('emergencyResult');

    // 确认对话框
    if (!confirm('确定要发送紧急求助信息吗？')) {
        return;
    }

    // 显示加载状态
    const originalText = emergencyBtn.innerHTML;
    emergencyBtn.innerHTML = '<div class="loading"></div> <span class="ms-2">正在发送...</span>';
    emergencyBtn.disabled = true;
    emergencyResult.innerHTML = '<div class="text-center"><div class="loading"></div> <span class="ms-2">正在发送求助信息...</span></div>';

    try {
        const response = await fetch('/api/emergency', {
            method: 'POST'
        });
        const data = await response.json();

        if (data.status === 'success') {
            emergencyResult.innerHTML = `
                <div class="alert alert-success">
                    <h6><i class="bi bi-check-circle"></i> 求助信息已发送</h6>
                    <p>已向 ${data.sent_count} 个紧急联系人发送求助信息</p>
                    <p>短信内容：紧急求助：我可能在${data.location?.city || '未知位置'}附近遇到麻烦，请尽快联系我。</p>
                </div>
            `;
        } else if (data.status === 'warning') {
            emergencyResult.innerHTML = `
                <div class="alert alert-warning">
                    <h6><i class="bi bi-exclamation-triangle"></i> 警告</h6>
                    <p>${data.message}</p>
                </div>
            `;
        } else {
            emergencyResult.innerHTML = `<div class="alert alert-danger">发送失败：${data.message}</div>`;
        }
    } catch (error) {
        console.error('发送求助信息失败:', error);
        emergencyResult.innerHTML = '<div class="alert alert-danger">发送失败：网络错误，请稍后重试</div>';
    } finally {
        // 恢复按钮状态
        emergencyBtn.innerHTML = originalText;
        emergencyBtn.disabled = false;
    }
}

// 处理智能问答表单提交
async function handleAskFormSubmit(e) {
    e.preventDefault();

    const formData = new FormData(e.target);
    const question = formData.get('question').trim();
    const askResult = document.getElementById('askResult');

    // 显示加载状态
    askResult.innerHTML = '<div class="text-center"><div class="loading"></div> <span class="ms-2">AI正在思考中...</span></div>';

    try {
        const response = await fetch('/api/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ question })
        });

        const data = await response.json();

        if (data.status === 'success' || data.status === 'warning') {
            // 显示回答
            let askHtml = `
                <div class="mb-3">
                    <h6>您的问题：</h6>
                    <p class="mb-0">${question}</p>
                </div>
                <div class="mb-3">
                    <h6>AI回答：</h6>
                    <p class="mb-0">${data.answer}</p>
                </div>
            `;

            if (data.status === 'warning') {
                askHtml += `
                    <div class="alert alert-warning mt-3">
                        <p class="mb-0">${data.message}</p>
                    </div>
                `;
            }

            askResult.innerHTML = askHtml;

            // 播放语音播报
            speakText(data.answer);
        } else {
            askResult.innerHTML = `<div class="alert alert-danger">提问失败：${data.message}</div>`;
        }
    } catch (error) {
        console.error('提问失败:', error);
        askResult.innerHTML = '<div class="alert alert-danger">提问失败：网络错误，请稍后重试</div>';
    }

    // 清空表单
    e.target.reset();
}

// 处理获取天气按钮点击
async function handleGetWeather() {
    const getWeatherBtn = document.getElementById('getWeatherBtn');
    const weatherResult = document.getElementById('weatherResult');

    // 显示加载状态
    const originalText = getWeatherBtn.innerHTML;
    getWeatherBtn.innerHTML = '<div class="loading"></div> <span class="ms-2">正在获取...</span>';
    getWeatherBtn.disabled = true;
    weatherResult.innerHTML = '<div class="text-center"><div class="loading"></div> <span class="ms-2">正在获取天气信息...</span></div>';

    try {
        let weatherUrl = '/api/weather';
        let locationUsed = false;

        // 检查是否有定位信息
        if (currentLocation) {
            if (currentLocationMethod === 'gps' && currentLocation.lat && currentLocation.lon) {
                // 使用GPS坐标查询天气
                weatherUrl = `/api/weather?lat=${currentLocation.lat}&lon=${currentLocation.lon}`;
                locationUsed = true;
                console.log('使用GPS坐标查询天气:', { lat: currentLocation.lat, lon: currentLocation.lon });
            } else if (currentLocationMethod === 'ip' && currentLocation.city) {
                // 使用城市名查询天气
                weatherUrl = `/api/weather?city=${encodeURIComponent(currentLocation.city)}`;
                locationUsed = true;
                console.log('使用城市名查询天气:', currentLocation.city);
            }
        }

        const response = await fetch(weatherUrl);
        const data = await response.json();

        if (data.status === 'success') {
            // 显示天气信息
            const weather = data.weather;
            const locationInfo = locationUsed ?
                `<div class="alert alert-success mt-3">
                    <small><i class="bi bi-geo-alt"></i> 位置：${currentLocationMethod === 'gps' ? 'GPS定位' : 'IP定位'} - ${currentLocation.city || currentLocation.address || '未知位置'}</small>
                </div>` : '';

            let weatherHtml = `
                <h6>当前天气：</h6>
                <div class="row">
                    <div class="col-6">
                        <ul class="result-list">
                            <li>城市：${weather.basic.city || '未知'}</li>
                            <li>省份：${weather.basic.province || '未知'}</li>
                            <li>更新时间：${weather.basic.update_time || '未知'}</li>
                        </ul>
                    </div>
                    <div class="col-6">
                        <ul class="result-list">
                            <li>天气：${weather.now.weather || '未知'}</li>
                            <li>温度：${weather.now.temperature || '未知'}°C</li>
                            <li>湿度：${weather.now.humidity || '未知'}%</li>
                            <li>风力：${weather.now.wind_direction || '未知'}风${weather.now.wind_power || '未知'}级</li>
                        </ul>
                    </div>
                </div>
                ${locationInfo}
                <div class="alert alert-info mt-3">
                    <h6><i class="bi bi-volume-up"></i> 语音播报：</h6>
                    <p>${data.announcement}</p>
                </div>
            `;
            weatherResult.innerHTML = weatherHtml;

            // 播放语音播报
            speakText(data.announcement);
        } else {
            // 如果使用位置信息查询失败，提示用户
            if (locationUsed) {
                weatherResult.innerHTML = `
                    <div class="alert alert-warning">
                        <h6><i class="bi bi-exclamation-triangle"></i> 使用定位查询失败</h6>
                        <p>${data.message}</p>
                        <p><strong>提示：</strong>您可以尝试手动输入城市名称进行查询</p>
                    </div>
                `;
            } else {
                weatherResult.innerHTML = `<div class="alert alert-danger">获取天气失败：${data.message}</div>`;
            }
        }
    } catch (error) {
        console.error('获取天气失败:', error);
        weatherResult.innerHTML = '<div class="alert alert-danger">获取天气失败：网络错误，请稍后重试</div>';
    } finally {
        // 恢复按钮状态
        getWeatherBtn.innerHTML = originalText;
        getWeatherBtn.disabled = false;
    }
}

// 处理按城市名称查询天气
async function handleGetWeatherByCity() {
    const cityInput = document.getElementById('cityInput');
    const city = cityInput.value.trim();
    const getWeatherByCityBtn = document.getElementById('getWeatherByCityBtn');
    const weatherResult = document.getElementById('weatherResult');

    if (!city) {
        alert('请输入城市名称');
        return;
    }

    // 显示加载状态
    const originalText = getWeatherByCityBtn.innerHTML;
    getWeatherByCityBtn.innerHTML = '<div class="loading"></div> <span class="ms-2">正在查询...</span>';
    getWeatherByCityBtn.disabled = true;
    weatherResult.innerHTML = `<div class="text-center"><div class="loading"></div> <span class="ms-2">正在查询${city}的天气信息...</span></div>`;

    try {
        const response = await fetch(`/api/weather?city=${encodeURIComponent(city)}`);
        const data = await response.json();

        if (data.status === 'success') {
            // 显示天气信息
            const weather = data.weather;
            let weatherHtml = `
                <h6>${city}的天气：</h6>
                <div class="row">
                    <div class="col-6">
                        <ul class="result-list">
                            <li>城市：${weather.basic.city || city}</li>
                            <li>省份：${weather.basic.province || '未知'}</li>
                            <li>更新时间：${weather.basic.update_time || '未知'}</li>
                        </ul>
                    </div>
                    <div class="col-6">
                        <ul class="result-list">
                            <li>天气：${weather.now.weather || '未知'}</li>
                            <li>温度：${weather.now.temperature || '未知'}°C</li>
                            <li>湿度：${weather.now.humidity || '未知'}%</li>
                            <li>风力：${weather.now.wind_direction || '未知'}风${weather.now.wind_power || '未知'}级</li>
                        </ul>
                    </div>
                </div>
                <div class="alert alert-info mt-3">
                    <h6><i class="bi bi-volume-up"></i> 语音播报：</h6>
                    <p>${data.announcement}</p>
                </div>
            `;
            weatherResult.innerHTML = weatherHtml;

            // 播放语音播报
            speakText(data.announcement);
        } else {
            weatherResult.innerHTML = `<div class="alert alert-danger">查询天气失败：${data.message}</div>`;
        }
    } catch (error) {
        console.error('查询天气失败:', error);
        weatherResult.innerHTML = '<div class="alert alert-danger">查询天气失败：网络错误，请稍后重试</div>';
    } finally {
        // 恢复按钮状态
        getWeatherByCityBtn.innerHTML = originalText;
        getWeatherByCityBtn.disabled = false;
    }
}

// ==================== ESP32后端代理功能 ====================

// 全局变量：是否使用后端代理
let useBackendProxy = false;

// 使用后端代理连接ESP32摄像头
async function connectWithProxy() {
    const urlInput = document.getElementById('espCameraUrl');
    if (!urlInput) return;

    const url = urlInput.value.trim();
    if (!url) {
        addLogEntry('请输入ESP32摄像头地址', 'error');
        return;
    }

    // 清理URL
    let cleanUrl = url.replace(/^(http:\/\/|https:\/\/)/, '');
    cleanUrl = cleanUrl.replace(/\/$/, '');

    addLogEntry(`使用后端代理连接: ${cleanUrl}`, 'info');

    try {
        // 1. 测试连接
        addLogEntry('步骤1: 测试连接...', 'info');
        const testResponse = await fetch(`/esp32/proxy/${cleanUrl}/test`, {
            method: 'POST'
        });
        const testResult = await testResponse.json();

        if (!testResult.success) {
            addLogEntry('连接测试失败', 'error');
            if (testResult.tests) {
                testResult.tests.forEach(t => {
                    if (t.error) {
                        addLogEntry(`  ${t.endpoint}: ${t.error}`, 'warning');
                    }
                });
            }
            return;
        }

        addLogEntry(`找到 ${testResult.available_endpoints.length} 个可用端点`, 'success');
        testResult.available_endpoints.forEach(ep => {
            addLogEntry(`  ✓ ${ep.url} (${ep.type})`, 'info');
        });

        // 2. 启动代理
        addLogEntry('步骤2: 启动视频流代理...', 'info');
        const startResponse = await fetch(`/esp32/proxy/${cleanUrl}/start`, {
            method: 'POST'
        });
        const startResult = await startResponse.json();

        if (!startResult.success) {
            addLogEntry('启动代理失败', 'error');
            return;
        }

        addLogEntry('代理已启动', 'success');

        // 3. 通过代理连接
        useBackendProxy = true;
        const proxyUrl = `/esp32/proxy/${cleanUrl}`;

        if (espCameraManager) {
            // 使用代理URL连接
            const connected = await espCameraManager.connect(proxyUrl);
            if (connected) {
                addLogEntry('通过后端代理连接成功!', 'success');
            }
        }

    } catch (error) {
        console.error('代理连接失败:', error);
        addLogEntry(`代理连接失败: ${error.message}`, 'error');
    }
}

// 停止后端代理
async function stopProxy() {
    const urlInput = document.getElementById('espCameraUrl');
    if (!urlInput) return;

    const url = urlInput.value.trim();
    if (!url) return;

    let cleanUrl = url.replace(/^(http:\/\/|https:\/\/)/, '');
    cleanUrl = cleanUrl.replace(/\/$/, '');

    try {
        await fetch(`/esp32/proxy/${cleanUrl}/stop`, {
            method: 'POST'
        });
        useBackendProxy = false;
        addLogEntry('后端代理已停止', 'info');
    } catch (error) {
        console.error('停止代理失败:', error);
    }
}

// 获取代理状态
async function getProxyStatus() {
    const urlInput = document.getElementById('espCameraUrl');
    if (!urlInput) return null;

    const url = urlInput.value.trim();
    if (!url) return null;

    let cleanUrl = url.replace(/^(http:\/\/|https:\/\/)/, '');
    cleanUrl = cleanUrl.replace(/\/$/, '');

    try {
        const response = await fetch(`/esp32/proxy/${cleanUrl}/status`);
        return await response.json();
    } catch (error) {
        console.error('获取代理状态失败:', error);
        return null;
    }
}

// 使用代理模式的检测函数
async function detectWithProxy() {
    if (!useBackendProxy || !espCameraManager) {
        addLogEntry('请先通过后端代理连接摄像头', 'warning');
        return;
    }

    const status = espCameraManager.getStatus();
    if (!status.isConnected || !status.isPlaying) {
        addLogEntry('摄像头未连接或未播放', 'error');
        return;
    }

    // 获取当前帧
    const canvas = document.getElementById('canvasElement');
    if (!canvas) return;

    addLogEntry('开始目标检测...', 'info');

    try {
        const imageData = canvas.toDataURL('image/jpeg', 0.8);

        const response = await fetch('/api/detect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                image: imageData,
                camera_type: 'esp32_proxy'
            })
        });

        const result = await response.json();

        if (result.status === 'success') {
            displayDetectionResults(result);

            if (result.objects && result.objects.length > 0) {
                const announcement = result.objects.map(obj =>
                    `${obj.class} 在 ${Math.round(obj.distance)} 米处`
                ).join('，');
                speakText('检测到：' + announcement);
            }
        } else {
            addLogEntry(`检测失败: ${result.message}`, 'error');
        }
    } catch (error) {
        console.error('检测失败:', error);
        addLogEntry(`检测失败: ${error.message}`, 'error');
    }
}