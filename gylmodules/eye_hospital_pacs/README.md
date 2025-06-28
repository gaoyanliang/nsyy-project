## 定时将指定目录中的文件转移至 统一共享目录中

在各个检查设备所在 windows 电脑上 按顺序执行如下步骤：

1. 用文本编辑器（推荐 VSCode 或记事本）新建一个文件，内容写好你的 `transfer.ps1` 脚本。
2. Windows 默认禁止运行脚本，需要设置允许脚本执行, 以管理员身份打开 PowerShell,  输入以下命令： Set-ExecutionPolicy RemoteSigned ,  出现提示，输入 `Y` 回车确认。
3. 测试脚本：打开普通 PowerShell（不用管理员）： .\transfer.ps1  如果脚本运行没有错误，就说明环境正常。
4. 给脚本加定时执行（推荐任务计划） 

Windows 自带的 wscript.exe 可以彻底隐藏控制台窗口。

步骤：
创建一个 VBS 脚本（如 E:\script\run_hidden.vbs），内容如下：
```shell
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "powershell.exe -NoLogo -NonInteractive -ExecutionPolicy Bypass -File ""E:\script\transfer.ps1""", 0, False
```
0 表示 完全隐藏窗口（无闪烁）。
False 表示 不等待脚本执行完成（避免阻塞）。
修改计划任务命令，改为调用 VBS 脚本：
```shell
schtasks /create /tn "每分钟执行一次同步文件" /tr "wscript.exe ""E:\script\run_hidden.vbs""" /sc minute /mo 1
```

✅ 彻底无窗口，适用于所有 Windows 版本。


脚本内容如下：

```shell
# 定义本地监控文件夹路径
$sourceFolder = "C:\WatchFolder"

# 定义目标共享文件夹路径
$destFolder = "\\TARGET-PC\SharedFolder"

# 记录已转移文件的记录文件路径（防止重复转移）
$recordFile = "$PSScriptRoot\transfer_record.txt"

# 读取已处理文件列表
if (Test-Path $recordFile) {
    $processedFiles = Get-Content $recordFile
} else {
    $processedFiles = @()
}

# 获取当前文件夹中所有文件
$currentFiles = Get-ChildItem -Path $sourceFolder -File

foreach ($file in $currentFiles) {
    # 如果文件未被处理过
    if (-not $processedFiles.Contains($file.Name)) {
        try {
            # 复制文件到目标共享文件夹
            Copy-Item -Path $file.FullName -Destination $destFolder -Force

            # 记录该文件名，避免重复处理
            Add-Content -Path $recordFile -Value $file.Name

            # 可选：复制成功后删除本地文件
            Remove-Item -Path $file.FullName -Force
        } catch {
            Write-Host "复制文件 $($file.Name) 失败： $_"
        }
    }
}
```

```shell
<#
.SYNOPSIS
监控本地文件夹并自动同步文件到共享目录，记录详细日志。 优化版-添加日志
#>

# 配置参数
$sourceFolder = "C:\WatchFolder"          # 本地监控文件夹
$destFolder = "\\TARGET-PC\SharedFolder"   # 目标共享文件夹
$recordFile = "$PSScriptRoot\transfer_record.txt"  # 已处理文件记录
$logFile = "$PSScriptRoot\transfer_log.txt"        # 日志文件路径
$deleteAfterCopy = $true                  # 复制后是否删除源文件

# 初始化日志函数
function Write-Log {
    param (
        [string]$Message,
        [string]$Level = "INFO"  # INFO/WARNING/ERROR
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"
    Add-Content -Path $logFile -Value $logEntry
    Write-Host $logEntry -ForegroundColor $(if ($Level -eq "ERROR") { "Red" } elseif ($Level -eq "WARNING") { "Yellow" } else { "White" })
}

# 检查必要目录是否存在
if (-not (Test-Path -Path $sourceFolder -PathType Container)) {
    Write-Log "本地监控文件夹不存在: $sourceFolder" -Level "ERROR"
    exit 1
}

if (-not (Test-Path -Path $destFolder -PathType Container)) {
    Write-Log "目标共享文件夹不可访问: $destFolder" -Level "ERROR"
    exit 1
}

# 初始化记录文件
if (-not (Test-Path $recordFile)) {
    New-Item -Path $recordFile -ItemType File -Force | Out-Null
    Write-Log "已创建新的记录文件: $recordFile"
}

# 读取已处理文件列表
try {
    $processedFiles = Get-Content $recordFile -ErrorAction Stop
} catch {
    Write-Log "读取记录文件失败: $_" -Level "ERROR"
    $processedFiles = @()
}

# 获取当前文件列表
try {
    $currentFiles = Get-ChildItem -Path $sourceFolder -File
    Write-Log "扫描到 $($currentFiles.Count) 个待处理文件"
} catch {
    Write-Log "获取文件列表失败: $_" -Level "ERROR"
    exit 1
}

# 处理文件
foreach ($file in $currentFiles) {
    if ($processedFiles -contains $file.Name) {
        Write-Log "跳过已处理文件: $($file.Name)"
        continue
    }

    try {
        # 复制文件
        $destPath = Join-Path -Path $destFolder -ChildPath $file.Name
        Copy-Item -Path $file.FullName -Destination $destPath -Force
        Write-Log "成功复制文件: $($file.Name) → $destFolder"

        # 记录到已处理列表
        Add-Content -Path $recordFile -Value $file.Name

        # 可选：删除源文件
        if ($deleteAfterCopy) {
            Remove-Item -Path $file.FullName -Force
            Write-Log "已删除源文件: $($file.FullName)"
        }
    } catch {
        Write-Log "处理文件 $($file.Name) 失败: $_" -Level "ERROR"
    }
}

Write-Log "文件同步完成"
```
























