function onTabClick(e) {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
    e.target.classList.add("active");
    document.getElementById("tab-" + e.target.dataset.tab).classList.add("active");
}

document.querySelectorAll(".tab-btn").forEach(b => b.onclick = onTabClick);

function onTextInput(e) {
    if (e.key === "Enter") {
        const input = document.getElementById("text-input");
        const text = input.value.trim();
        if (text) {
            addUserMsg(text);
            addSystemMsg("[AI回复]: 语音回复通过 RTC 音频通道播放");
            input.value = "";
        }
    }
}

async function sendText() {
    const input = document.getElementById("text-input");
    const text = input.value.trim();
    if (text) {
        addUserMsg(text);
        addSystemMsg("[AI回复]: 语音回复通过 RTC 音频通道播放");
        input.value = "";
    }
}

function addUserMsg(text) {
    const log = document.getElementById("conversation-log");
    const div = document.createElement("div");
    div.className = "msg user";
    div.innerHTML = "<strong>[你]:</strong> " + text;
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
}

function onImageSelected(e) {
    const file = e.target.files[0];
    if (!file) return;
    document.getElementById("image-name").textContent = file.name;

    const reader = new FileReader();
    reader.onload = (ev) => {
        const preview = document.getElementById("image-preview");
        preview.innerHTML = `<img src="${ev.target.result}" alt="预览">`;
    };
    reader.readAsDataURL(file);
}

async function sendImage() {
    const input = document.getElementById("image-input");
    const prompt = document.getElementById("image-prompt").value.trim();
    if (!input.files.length) {
        addSystemMsg("请先选择一张图片");
        return;
    }
    const file = input.files[0];
    addUserMsg("[发送图片] " + file.name);
    if (prompt) addUserMsg(prompt);
    addSystemMsg("[AI回复]: 图片已发送，语音回复通过 RTC 音频通道播放");
}

function interruptAgent() {
    if (typeof window.interruptAgentRTC === "function") {
        window.interruptAgentRTC();
    }
    addSystemMsg("已发送打断请求");
}