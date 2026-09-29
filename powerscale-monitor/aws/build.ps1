# Build script for creating Lambda deployment package (Windows)

Write-Host "Building Lambda deployment package..." -ForegroundColor Green

# Clean up previous builds
if (Test-Path "package") {
    Remove-Item -Recurse -Force package
}
if (Test-Path "deployment.zip") {
    Remove-Item -Force deployment.zip
}

# Create package directory
New-Item -ItemType Directory -Force package | Out-Null

# Copy Lambda function
Copy-Item lambda_function.py package\

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
Set-Location package
pip install -r ..\aws-requirements.txt -t .
Set-Location ..

# Create zip file
Write-Host "Creating deployment package..." -ForegroundColor Yellow
Compress-Archive -Path package\* -DestinationPath deployment.zip -Force

# Clean up package directory
Remove-Item -Recurse -Force package

Write-Host "Build complete! deployment.zip created." -ForegroundColor Green
$size = (Get-Item deployment.zip).Length / 1KB
Write-Host "Size: $([math]::Round($size, 2)) KB" -ForegroundColor Cyan
