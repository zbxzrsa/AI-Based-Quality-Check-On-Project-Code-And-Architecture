#!/usr/bin/env pwsh
# Fix Next.js development server issues

Write-Host "🔧 Fixing Next.js development server..." -ForegroundColor Cyan

# Step 1: Stop any running Next.js processes
Write-Host "`n📌 Step 1: Stopping any running Next.js processes..." -ForegroundColor Yellow
$nextProcesses = Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*node_modules*next*" }
if ($nextProcesses) {
    $nextProcesses | Stop-Process -Force
    Write-Host "✅ Stopped running Next.js processes" -ForegroundColor Green
} else {
    Write-Host "ℹ️  No running Next.js processes found" -ForegroundColor Gray
}

# Step 2: Clean build artifacts and cache
Write-Host "`n📌 Step 2: Cleaning build artifacts and cache..." -ForegroundColor Yellow
$dirsToRemove = @(".next", ".swc", "node_modules/.cache")
foreach ($dir in $dirsToRemove) {
    if (Test-Path $dir) {
        Remove-Item -Recurse -Force $dir
        Write-Host "✅ Removed $dir" -ForegroundColor Green
    } else {
        Write-Host "ℹ️  $dir not found (already clean)" -ForegroundColor Gray
    }
}

# Step 3: Reinstall dependencies
Write-Host "`n📌 Step 3: Reinstalling dependencies..." -ForegroundColor Yellow
Write-Host "This may take a few minutes..." -ForegroundColor Gray
npm install
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Dependencies installed successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
    exit 1
}

# Step 4: Verify Next.js installation
Write-Host "`n📌 Step 4: Verifying Next.js installation..." -ForegroundColor Yellow
$nextVersion = npm list next --depth=0 2>$null | Select-String "next@"
if ($nextVersion) {
    Write-Host "✅ $nextVersion" -ForegroundColor Green
} else {
    Write-Host "⚠️  Could not verify Next.js version" -ForegroundColor Yellow
}

Write-Host "`n✨ Fix complete! You can now run:" -ForegroundColor Cyan
Write-Host "   npm run dev" -ForegroundColor White
Write-Host "`nThe development server should start at http://localhost:3000" -ForegroundColor Gray
