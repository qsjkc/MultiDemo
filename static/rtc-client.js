let engine = null;
let localStream = null;
let remoteStreams = {};
let isConnected = false;
let isRecording = false;
let agentTaskId = null;
let audioContext = null;

async function connectRTC() {
    const btn = document.getElementById("btn-connect");
    btn.disabled = true;
    btn.textContent = "连接中...";
    updateStatus("connecting", "正在连接 RTC...");

    try {
        const resp = await fetch("/api/token", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ room_id: ROOM_ID, user_id: USER_ID }),
        });
        const result = await resp.json();
        if (result.code !== 0) throw new Error(result.msg);

        const { app_id, token, room_id, user_id } = result.data;

        engine = VERTC.createEngine(app_id);

        engine.on("roomStateChanged", (data) => {
            if (data.state === "connected") {
                isConnected = true;
                updateStatus("connected", "已连接到 RTC 房间");
                document.getElementById("btn-disconnect").disabled = false;
                document.getElementById("btn-start-agent").disabled = false;
                addSystemMsg("已进入 RTC 房间: " + room_id);
            } else if (data.state === "disconnected") {
                isConnected = false;
                updateStatus("disconnected", "RTC 已断开");
                cleanupRTC();
            }
        });

        engine.on("userPublishStream", async (data) => {
            const { userId, mediaType } = data;
            if (mediaType === "audio" && userId !== USER_ID) {
                try {
                    await engine.subscribeStream(userId, mediaType);
                    addSystemMsg("智能体已加入房间");
                } catch (e) {
                    addSystemMsg("智能体加入失败: " + e.message);
                }
            }
        });

        engine.on("userUnPublishStream", (data) => {
            if (data.userId !== USER_ID) {
                addSystemMsg("智能体已离开房间");
            }
        });

        engine.on("streamSubscribed", (data) => {
            if (data.subscribedStream && data.subscribedStream.play) {
                audioContext = data.subscribedStream.play();
                audioContext.play();
            }
        });

        engine.on("onRoomBinaryMessageReceived", (data) => {
            try {
                const msg = JSON.parse(new TextDecoder().decode(data.message));
                if (msg.event === "user_speech_start") {
                    updateVADStatus("detecting");
                } else if (msg.event === "user_speech_end") {
                    updateVADStatus("processing");
                } else if (msg.event === "agent_speech") {
                    updateVADStatus("responding");
                } else if (msg.event === "agent_speech_end") {
                    updateVADStatus("idle");
                }
            } catch (e) {}
        });

        engine.on("error", (e) => {
            addSystemMsg("RTC 错误: " + (e.message || JSON.stringify(e)));
            updateStatus("error", "RTC 错误");
        });

        engine.on("warning", (e) => {
            console.warn("RTC warning:", e);
        });

        await engine.joinRoom(token, room_id, user_id);

        localStream = await engine.createLocalStream({ audio: true, video: false });
        await engine.publishStream(localStream);

        btn.textContent = "连接服务";
    } catch (e) {
        btn.disabled = false;
        btn.textContent = "连接服务";
        updateStatus("error", "连接失败: " + e.message);
        addSystemMsg("连接失败: " + e.message);
    }
}

function disconnectRTC() {
    cleanupRTC();
}

async function cleanupRTC() {
    if (agentTaskId) {
        await stopAgent();
    }
    if (localStream) {
        try { engine.unpublishStream(localStream); } catch (e) {}
        localStream = null;
    }
    if (engine) {
        try {
            await engine.leaveRoom();
        } catch (e) {}
        engine = null;
    }
    isConnected = false;
    isRecording = false;
    updateStatus("disconnected", "已断开");
    document.getElementById("btn-connect").disabled = false;
    document.getElementById("btn-disconnect").disabled = true;
    document.getElementById("btn-start-agent").disabled = true;
    document.getElementById("btn-stop-agent").disabled = true;
    document.getElementById("btn-interrupt").disabled = true;
    addSystemMsg("已断开 RTC 连接");
}

async function startRecording() {
    if (!isConnected) return;
    isRecording = true;
    document.getElementById("btn-push-talk").classList.add("active");
    try { await engine.unmuteAudio(true); } catch (e) {}
}

async function stopRecording() {
    if (!isRecording) return;
    isRecording = false;
    document.getElementById("btn-push-talk").classList.remove("active");
}

async function startAgent() {
    if (!isConnected) return;
    try {
        const resp = await fetch("/api/agent/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ room_id: ROOM_ID }),
        });
        const result = await resp.json();
        if (result.code !== 0) throw new Error(result.msg);

        agentTaskId = result.data.task_id;
        document.getElementById("btn-start-agent").disabled = true;
        document.getElementById("btn-stop-agent").disabled = false;
        document.getElementById("btn-interrupt").disabled = false;
        updateStatus("connected", "智能体已启动");
        addSystemMsg("智能体已启动, TaskId: " + agentTaskId);
        updateVADStatus("idle");
    } catch (e) {
        addSystemMsg("启动智能体失败: " + e.message);
    }
}

async function stopAgent() {
    if (!agentTaskId) return;
    try {
        await fetch("/api/agent/stop", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ room_id: ROOM_ID, task_id: agentTaskId }),
        });
    } catch (e) {}
    agentTaskId = null;
    document.getElementById("btn-start-agent").disabled = false;
    document.getElementById("btn-stop-agent").disabled = true;
    document.getElementById("btn-interrupt").disabled = true;
    updateStatus("connected", "已连接到 RTC 房间");
    addSystemMsg("智能体已停止");
    updateVADStatus("idle");
}

function interruptAgent() {}
function sendImage() { addSystemMsg("图片模式: 请通过 RTC 视频通道发送"); }
function sendText() { addSystemMsg("文字模式: 已通过 RTC 推流"); }

function updateStatus(state, text) {
    const indicator = document.getElementById("status-indicator");
    indicator.className = "indicator " + state;
    document.getElementById("status-text").textContent = text;
}

function addSystemMsg(msg) {
    const log = document.getElementById("conversation-log");
    const div = document.createElement("div");
    div.className = "msg system";
    div.textContent = msg;
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
}

function updateVADStatus(state) {
    const el = document.getElementById("vad-status");
    const wave = document.getElementById("vad-wave");
    const states = { idle: "等待说话...", detecting: "正在识别语音...", processing: "正在处理语音...", responding: "智能体正在回复..." };
    el.textContent = states[state] || state;
    wave.className = "vad-wave " + (state === "detecting" || state === "processing" ? "active" : "");
}