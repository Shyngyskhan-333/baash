# LexEntropy Quick Setup Script (Windows)
# This script ensures dependencies are installed correctly and handles common encoding issues.

Write-Host "🚀 Starting LexEntropy Setup..." -ForegroundColor Cyan

# 1. Backend Setup
Write-Host "`n📦 Setting up Backend..." -ForegroundColor Yellow
if (-not (Test-Path "venv")) {
    python -m venv venv
    Write-Host "✅ Virtual environment created."
} else {
    Write-Host "ℹ️ Virtual environment already exists."
}

# Install Python requirements
Write-Host "💾 Installing Python dependencies..."
.\venv\Scripts\pip.exe install -r requirements.txt
Write-Host "✅ Python dependencies installed."

# 2. Environment Configuration
if (-not (Test-Path ".env")) {
    Write-Host "📝 Creating .env from .env.example..."
    # Explicitly use UTF-8 without BOM to avoid encoding issues
    $content = Get-Content .env.example -Raw
    [System.IO.File]::WriteAllText("$PSScriptRoot\.env", $content, [System.Text.UTF8Encoding]::new($false))
    Write-Host "✅ .env created (UTF-8 encoding)."
} else {
    Write-Host "ℹ️ .env already exists."
}

# 3. Frontend Setup
Write-Host "`n🖥️ Setting up Frontend..." -ForegroundColor Yellow
if (Test-Path "frontend") {
    Push-Location frontend
    Write-Host "💾 Installing NPM dependencies..."
    npm install
    Pop-Location
    Write-Host "✅ Frontend dependencies installed."
} else {
    Write-Warning "❌ Frontend directory not found!"
}

Write-Host "`n🎉 Setup complete! Use these commands to start:" -ForegroundColor Green
Write-Host "Backend: .\venv\Scripts\uvicorn.exe api.main:app --port 8000 --reload"
Write-Host "Frontend: cd frontend; npm run dev"
