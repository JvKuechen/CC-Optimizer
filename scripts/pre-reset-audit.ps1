# Pre-Reset Audit: Things that won't survive "Reset this PC (keep files)"
# "Keep files" preserves: user profile folders (Desktop, Documents, Downloads, etc.)
# "Keep files" REMOVES: installed apps, drivers, settings outside user profile

Write-Host "=== NON-MICROSOFT SCHEDULED TASKS ===" -ForegroundColor Cyan
Get-ScheduledTask | Where-Object {
    $_.Author -and $_.Author -notmatch 'Microsoft|Windows|\$'
} | Select-Object TaskName, TaskPath, State, Author | Format-Table -AutoSize

Write-Host "`n=== THIRD-PARTY SERVICES ===" -ForegroundColor Cyan
Get-CimInstance Win32_Service | Where-Object {
    $_.StartMode -ne 'Disabled' -and
    $_.PathName -and
    $_.PathName -notmatch 'Windows|Microsoft|svchost|System32|SysWOW64'
} | Select-Object Name, DisplayName, StartMode, State |
    Sort-Object DisplayName | Format-Table -AutoSize

Write-Host "`n=== INSTALLED PROGRAMS ===" -ForegroundColor Cyan
$paths = @(
    'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
    'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
    'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*'
)
Get-ItemProperty $paths -ErrorAction SilentlyContinue |
    Where-Object { $_.DisplayName } |
    Select-Object DisplayName, Publisher, DisplayVersion |
    Sort-Object DisplayName | Format-Table -AutoSize

Write-Host "`n=== WINDOWS OPTIONAL FEATURES (Enabled) ===" -ForegroundColor Cyan
Get-WindowsOptionalFeature -Online |
    Where-Object { $_.State -eq 'Enabled' } |
    Select-Object FeatureName | Sort-Object FeatureName | Format-Table -AutoSize

Write-Host "`n=== ENVIRONMENT VARIABLES (User) ===" -ForegroundColor Cyan
[Environment]::GetEnvironmentVariables('User') | Format-Table -AutoSize

Write-Host "`n=== ENVIRONMENT VARIABLES (Machine, non-default) ===" -ForegroundColor Cyan
$defaults = @('ComSpec','NUMBER_OF_PROCESSORS','OS','PATHEXT','PROCESSOR_ARCHITECTURE',
    'PROCESSOR_IDENTIFIER','PROCESSOR_LEVEL','PROCESSOR_REVISION','PSModulePath',
    'TEMP','TMP','USERNAME','windir','SystemRoot','SystemDrive','ProgramFiles',
    'ProgramFiles(x86)','ProgramData','ProgramW6432','CommonProgramFiles',
    'CommonProgramFiles(x86)','CommonProgramW6432','DriverData','ALLUSERSPROFILE')
[Environment]::GetEnvironmentVariables('Machine').GetEnumerator() |
    Where-Object { $_.Key -notin $defaults -and $_.Key -ne 'Path' } |
    Sort-Object Key | Format-Table -AutoSize

Write-Host "`n=== SYSTEM PATH (non-Windows entries) ===" -ForegroundColor Cyan
$env:Path -split ';' | Where-Object {
    $_ -and $_ -notmatch 'Windows|System32|SysWOW64|WindowsApps|Wbem'
} | ForEach-Object { Write-Host "  $_" }

Write-Host "`n=== GIT GLOBAL CONFIG ===" -ForegroundColor Cyan
git config --global --list 2>$null

Write-Host "`n=== SSH KEYS ===" -ForegroundColor Cyan
if (Test-Path "$env:USERPROFILE\.ssh") {
    Get-ChildItem "$env:USERPROFILE\.ssh" -File | Select-Object Name, Length | Format-Table -AutoSize
} else { Write-Host "  No .ssh directory" }

Write-Host "`n=== CLAUDE CODE CONFIG ===" -ForegroundColor Cyan
if (Test-Path "$env:USERPROFILE\.claude") {
    Write-Host "  ~/.claude/ exists (conversation history, settings, projects)"
    Write-Host "  Size:"
    $size = (Get-ChildItem "$env:USERPROFILE\.claude" -Recurse -File -ErrorAction SilentlyContinue |
        Measure-Object -Property Length -Sum).Sum
    Write-Host "  $([math]::Round($size / 1MB, 1)) MB total"
} else { Write-Host "  No .claude directory" }

Write-Host "`n=== WSL DISTRIBUTIONS ===" -ForegroundColor Cyan
wsl --list --verbose 2>$null

Write-Host "`n=== WINGET INSTALLED (non-Microsoft) ===" -ForegroundColor Cyan
winget list 2>$null | Where-Object { $_ -and $_ -notmatch 'Microsoft\.' }

Write-Host "`n=== STARTUP ITEMS ===" -ForegroundColor Cyan
Get-CimInstance Win32_StartupCommand | Select-Object Name, Command, Location | Format-Table -AutoSize

Write-Host "`n=== NETWORK ADAPTER BINDINGS ===" -ForegroundColor Cyan
Get-NetAdapterBinding -Name "Ethernet" |
    Where-Object { $_.Enabled -eq $true } |
    Select-Object DisplayName, ComponentID | Format-Table -AutoSize

Write-Host "`n=== FIREWALL RULES (non-default) ===" -ForegroundColor Cyan
Get-NetFirewallRule |
    Where-Object { $_.DisplayGroup -and $_.DisplayGroup -notmatch 'Core Networking|File and Printer|mDNS|Delivery Optimization|Hyper-V' -and $_.Enabled -eq 'True' } |
    Select-Object DisplayName, Direction, Action, Profile |
    Sort-Object DisplayName | Format-Table -AutoSize

Write-Host "`n=== DONE ===" -ForegroundColor Green
