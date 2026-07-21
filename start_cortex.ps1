cd D:\AI-Trader

Start-Transcript -Path D:\AI-Trader\startup_log.txt -Append


# Correct Cortex Python environment
$python = "D:\AI-Trader\venv\Scripts\python.exe"


# Start Ollama if not running
$ollama = Get-Process ollama -ErrorAction SilentlyContinue

if (-not $ollama) {

    Start-Process "ollama" -ArgumentList "serve"

    Start-Sleep -Seconds 10

    Write-Output "Ollama started"

}
else {

    Write-Output "Ollama already running"

}



# Start Cortex trading engine if not running
$cortex = Get-CimInstance Win32_Process |
Where-Object {

    $_.CommandLine -like "*D:\AI-Trader\autonomous_controller.py*"

}



if (-not $cortex) {


    Start-Process $python `
    -WorkingDirectory "D:\AI-Trader" `
    -ArgumentList "D:\AI-Trader\autonomous_controller.py"


    Write-Output "Cortex started"


}
else {


    Write-Output "Cortex already running"


}



# Start Discord bot if not running
$discord = Get-CimInstance Win32_Process |
Where-Object {

    $_.CommandLine -like "*D:\AI-Trader\cortex_discord.py*"

}



if (-not $discord) {


    Start-Process $python `
    -WorkingDirectory "D:\AI-Trader" `
    -ArgumentList "D:\AI-Trader\cortex_discord.py"


    Write-Output "Discord started"


}
else {


    Write-Output "Discord already running"


}



Stop-Transcript