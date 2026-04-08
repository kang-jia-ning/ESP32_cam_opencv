// 语音播报功能测试脚本
// 用于验证修复后的语音播报队列机制

// 模拟语音播报函数（简化版，用于测试）
function testSpeechQueue() {
    console.log("=== 语音播报队列功能测试 ===");
    
    // 模拟语音播报队列
    let speechQueue = [];
    let isSpeaking = false;
    let speechCount = 0;
    
    function speakText(text) {
        speechQueue.push(text);
        if (!isSpeaking) {
            processSpeechQueue();
        }
    }
    
    function processSpeechQueue() {
        if (speechQueue.length === 0) {
            isSpeaking = false;
            console.log("✅ 语音队列已清空");
            return;
        }
        
        isSpeaking = true;
        const text = speechQueue.shift();
        speechCount++;
        
        console.log(`🎯 播放第${speechCount}条语音: "${text}"`);
        console.log(`   队列中还有 ${speechQueue.length} 条语音等待播放`);
        
        // 模拟语音播放时间（根据文本长度计算）
        const speechDuration = text.length * 100; // 每字符100毫秒
        
        setTimeout(() => {
            console.log(`✅ 第${speechCount}条语音播放完成`);
            
            // 模拟语音播放间隔
            setTimeout(() => {
                processSpeechQueue();
            }, 500);
        }, speechDuration);
    }
    
    // 测试用例1：快速连续发送多条语音
    console.log("\n📋 测试用例1：快速连续发送多条语音");
    speakText("前方检测到行人");
    speakText("左前方有车辆");
    speakText("右方有自行车");
    speakText("当前视野内未检测到关键目标");
    
    // 测试用例2：在播放过程中添加新语音
    setTimeout(() => {
        console.log("\n📋 测试用例2：在播放过程中添加新语音");
        speakText("新增检测到交通标志");
    }, 1500);
    
    // 测试用例3：清空队列测试
    setTimeout(() => {
        console.log("\n📋 测试用例3：清空队列测试");
        speechQueue = [];
        isSpeaking = false;
        console.log("✅ 队列已手动清空");
    }, 4000);
}

// 运行测试
testSpeechQueue();