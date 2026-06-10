// ============================
// 浏览器录音模块 — AudioContext PCM直采版
// ============================
let audioContext = null;
let mediaStream = null;
let scriptProcessor = null;
let pcmChunks = [];
let recordingTimer = null;
let recordingSeconds = 0;
let audioWavBlob = null;

async function toggleRecording() {
    if (audioContext && audioContext.state !== 'closed') {
        stopRecording();
        return;
    }
    startRecording();
}

async function startRecording() {
    try {
        mediaStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                channelCount: 1,
                sampleRate: 16000,
                echoCancellation: true,
                noiseSuppression: true
            }
        });

        audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
        const source = audioContext.createMediaStreamSource(mediaStream);

        // ScriptProcessorNode — 直接获取 PCM 原始数据
        scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);
        pcmChunks = [];
        recordingSeconds = 0;

        scriptProcessor.onaudioprocess = (event) => {
            if (!audioContext) return;
            const input = event.inputBuffer.getChannelData(0);

            // Float32 [-1,1] → Int16 [-32768,32767]
            const int16Buffer = new Int16Array(input.length);
            for (let i = 0; i < input.length; i++) {
                const s = Math.max(-1, Math.min(1, input[i]));
                int16Buffer[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
            }
            pcmChunks.push(int16Buffer);
        };

        source.connect(scriptProcessor);
        scriptProcessor.connect(audioContext.destination);

        // UI 更新
        document.getElementById('recordBtn').classList.add('recording');
        document.getElementById('recordBtn').textContent = '⏹️';
        document.getElementById('recordHint').textContent = '正在录音中...';
        document.getElementById('recognizeRecordBtn').disabled = true;
        document.getElementById('analyzeRecordBtn').style.display = 'none';
        document.getElementById('recordResultCard').style.display = 'none';

        recordingTimer = setInterval(() => {
            recordingSeconds++;
            const mins = Math.floor(recordingSeconds / 60);
            const secs = recordingSeconds % 60;
            document.getElementById('recordTime').textContent =
                String(mins).padStart(2, '0') + ':' + String(secs).padStart(2, '0');
        }, 1000);

    } catch (err) {
        alert('无法访问麦克风: ' + err.message);
        console.error('录音错误:', err);
    }
}

function stopRecording() {
    if (scriptProcessor) {
        scriptProcessor.disconnect();
        scriptProcessor = null;
    }
    if (audioContext && audioContext.state !== 'closed') {
        audioContext.close();
        audioContext = null;
    }
    if (mediaStream) {
        mediaStream.getTracks().forEach(t => t.stop());
        mediaStream = null;
    }
    if (recordingTimer) {
        clearInterval(recordingTimer);
        recordingTimer = null;
    }

    // 合并所有 PCM 数据并生成 WAV
    if (pcmChunks.length > 0) {
        const totalLength = pcmChunks.reduce((sum, buf) => sum + buf.length, 0);
        const pcmData = new Int16Array(totalLength);
        let offset = 0;
        for (const chunk of pcmChunks) {
            pcmData.set(chunk, offset);
            offset += chunk.length;
        }

        const wavBuffer = encodeWAV(pcmData, 16000, 1, 16);
        audioWavBlob = new Blob([wavBuffer], { type: 'audio/wav' });
        console.log('录音完成: WAV, 大小:', (audioWavBlob.size / 1024).toFixed(1), 'KB, 时长:', recordingSeconds, '秒');
    }

    document.getElementById('recordBtn').classList.remove('recording');
    document.getElementById('recordBtn').textContent = '🎤';
    document.getElementById('recordHint').textContent = '录音已完成，点击"识别录音内容"开始识别';
    document.getElementById('recognizeRecordBtn').disabled = false;
}

function encodeWAV(samples, sampleRate, numChannels, bitsPerSample) {
    const byteRate = sampleRate * numChannels * bitsPerSample / 8;
    const blockAlign = numChannels * bitsPerSample / 8;
    const dataSize = samples.length * bitsPerSample / 8;
    const buffer = new ArrayBuffer(44 + dataSize);
    const view = new DataView(buffer);

    // RIFF header
    writeString(view, 0, 'RIFF');
    view.setUint32(4, 36 + dataSize, true);
    writeString(view, 8, 'WAVE');

    // fmt chunk
    writeString(view, 12, 'fmt ');
    view.setUint32(16, 16, true);                    // PCM
    view.setUint16(20, 1, true);                      // format = PCM
    view.setUint16(22, numChannels, true);             // channels
    view.setUint32(24, sampleRate, true);              // sampleRate
    view.setUint32(28, byteRate, true);                // byteRate
    view.setUint16(32, blockAlign, true);              // blockAlign
    view.setUint16(34, bitsPerSample, true);           // bitsPerSample

    // data chunk
    writeString(view, 36, 'data');
    view.setUint32(40, dataSize, true);

    // PCM samples
    let offset = 44;
    for (let i = 0; i < samples.length; i++, offset += 2) {
        view.setInt16(offset, samples[i], true);
    }

    return buffer;
}

function writeString(view, offset, str) {
    for (let i = 0; i < str.length; i++) {
        view.setUint8(offset + i, str.charCodeAt(i));
    }
}

function recognizeRecording() {
    if (!audioWavBlob) {
        alert('请先录制音频');
        return;
    }

    const btn = document.getElementById('recognizeRecordBtn');
    const resultCard = document.getElementById('recordResultCard');
    const resultBox = document.getElementById('recordResult');

    btn.disabled = true;
    btn.textContent = '⏳ 识别中...';
    resultCard.style.display = 'block';
    resultBox.textContent = '正在识别，请稍候...';

    fetch('/api/speech/recognize-blob', {
        method: 'POST',
        headers: { 'Content-Type': 'application/octet-stream' },
        body: audioWavBlob
    })
    .then(r => r.json())
    .then(data => {
        btn.disabled = false;
        btn.textContent = '🔍 识别录音内容';
        if (data.success) {
            resultBox.textContent = data.text;
            currentOriginalText = data.text;
            document.getElementById('analyzeRecordBtn').style.display = 'inline-flex';
            document.getElementById('analyzeRecordBtn').disabled = false;
        } else {
            resultBox.innerHTML = `<span style="color: var(--danger);">❌ ${data.error}</span>`;
        }
    })
    .catch(err => {
        btn.disabled = false;
        btn.textContent = '🔍 识别录音内容';
        resultBox.textContent = '网络请求出错: ' + err.message;
    });
}

function analyzeRecording() {
    if (!currentOriginalText) {
        alert('请先识别录音');
        return;
    }
    document.getElementById('pasteText').value = currentOriginalText;
    switchTab('paste');
    analyzePastedText();
}
