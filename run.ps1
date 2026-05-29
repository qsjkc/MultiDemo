# 火山引擎 RTC + 第三方 Agent 语音对话 Demo
# 快速启动脚本 (PowerShell)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " 火山引擎 RTC 语音对话 Demo" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 .env 文件
if (-not (Test-Path ".env")) {
    Write-Host "[WARNING] 未找到 .env 文件，请从 .env.example 复制并填写配置" -ForegroundColor Yellow
    Write-Host "  cp .env.example .env" -ForegroundColor Gray
    Write-Host ""
}

# 加载环境变量
if (Test-Path ".env") {
    Get-Content .env | ForEach-Object {
        if ($_ -match '^\s*([^#=]+)=(.*)$' -and $matches[1] -notmatch '^\s*$') {
            $key = $matches[1].Trim()
            $val = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($key, $val, "Process")
        }
    }
    Write-Host "[OK] 环境变量已加载" -ForegroundColor Green
}

Write-Host ""
Write-Host "请选择启动模式:" -ForegroundColor Yellow
Write-Host "  1) 客户端 (本地浏览器 RTC 对话)" -ForegroundColor White
Write-Host "  2) Agent 服务器 (部署到云服务器)" -ForegroundColor White
Write-Host "  3) 全部 (同时启动客户端和 Agent)" -ForegroundColor White
Write-Host ""

$choice = Read-Host "输入选项 (1/2/3)"

switch ($choice) {
    "1" {
        Write-Host ""
        Write-Host "[启动] 客户端后端..." -ForegroundColor Green
        pip install -r client-backend\requirements.txt 2>$null
        python client-backend\server.py
    }
    "2" {
        Write-Host ""
        Write-Host "[启动] Agent 服务器..." -ForegroundColor Green
        pip install -r agent-server\requirements.txt 2>$null
        python agent-server\server.py
    }
    "3" {
        Write-Host ""
        Write-Host "[启动] Agent 服务器 (后台)..." -ForegroundColor Green
        Start-Process python -ArgumentList "agent-server\server.py" -WindowStyle Hidden
        Start-Sleep -Seconds 2
        Write-Host "[启动] 客户端后端..." -ForegroundColor Green
        pip install -r client-backend\requirements.txt 2>$null
        Start-Process python -ArgumentList "client-backend\server.py" -WindowStyle Hidden
        Start-Sleep -Seconds 2
        Write-Host ""
        Write-Host "[OK] 服务已启动!" -ForegroundColor Green
        Write-Host "  客户端: http://localhost:5000" -ForegroundColor Cyan
        Write-Host "  Agent:  http://localhost:8080/health" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "按任意键停止所有服务..." -ForegroundColor Yellow
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        Get-Process python | Where-Object { $_.MainWindowTitle -eq "" } | Stop-Process -Force
        Write-Host "[OK] 服务已停止" -ForegroundColor Green
    }
    default {
        Write-Host "无效选项" -ForegroundColor Red
    }
}