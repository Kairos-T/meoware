$pythonPath = Get-Command python | Select-Object -ExpandProperty Source

if (-not $pythonPath) {
    Write-Host "Python is not installed or not found in the PATH."
    exit 1
}

$scriptPath = Join-Path $PSScriptRoot "main.py" 
$iconPath = Join-Path $PSScriptRoot "spotify.ico"
$requirementsPath = Join-Path $PSScriptRoot "requirements.txt"

# Check if PyInstaller is installed, if not, install it
$pyinstallerInstalled = & $pythonPath -m pip show pyinstaller
if (-not $pyinstallerInstalled) {
    Write-Host "Installing PyInstaller..."
    & $pythonPath -m pip install pyinstaller
}

# Install dependencies from requirements.txt
# if (Test-Path $requirementsPath) {
#     Write-Host "Installing dependencies from requirements.txt..."
#     & $pythonPath -m pip install -r $requirementsPath
# } else {
#     Write-Host "requirements.txt not found. Skipping dependency installation."
# }

# Compile into executable
$exeName = "spotify.exe"
Write-Host "Compiling $scriptPath into $exeName..."
& $pythonPath -m PyInstaller --onefile --noconsole --icon=$iconPath --distpath=$PSScriptRoot $scriptPath

Write-Host "Build complete. The executable is located in the 'dist' folder."
