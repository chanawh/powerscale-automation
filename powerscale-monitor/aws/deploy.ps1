# Deployment script for PowerScale Cloud Monitor Lambda function (Windows)

# Configuration
$FUNCTION_NAME = "powerscale-monitor"
$ROLE_NAME = "powerscale-monitor-role"
$S3_BUCKET = $env:S3_BUCKET
if (-not $S3_BUCKET) {
    $S3_BUCKET = "your-deployment-bucket"
}
$REGION = $env:AWS_REGION
if (-not $REGION) {
    $REGION = "us-east-1"
}

Write-Host "Deploying PowerScale Cloud Monitor..." -ForegroundColor Green

# Create deployment package
Write-Host "Creating deployment package..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force package | Out-Null
Copy-Item lambda_function.py package\
Set-Location package
pip install -r ..\requirements.txt -t .
Set-Location ..
Compress-Archive -Path package\* -DestinationPath deployment.zip -Force

# Upload to S3 (optional)
if ($S3_BUCKET -ne "your-deployment-bucket") {
    Write-Host "Uploading to S3..." -ForegroundColor Yellow
    aws s3 cp deployment.zip s3://$S3_BUCKET/powerscale-monitor/deployment.zip
    $S3_KEY = "s3://$S3_BUCKET/powerscale-monitor/deployment.zip"
} else {
    $S3_KEY = "fileb://deployment.zip"
}

# Create IAM role if it doesn't exist
Write-Host "Setting up IAM role..." -ForegroundColor Yellow
$roleExists = aws iam get-role --role-name $ROLE_NAME --region $REGION 2>&1
if ($LASTEXITCODE -ne 0) {
    aws iam create-role --role-name $ROLE_NAME --assume-role-policy-document file://iam-trust-policy.json --region $REGION
    aws iam put-role-policy --role-name $ROLE_NAME --policy-name PowerScaleMonitorPolicy --policy-document file://iam-policy.json --region $REGION
    Write-Host "Waiting for role to propagate..." -ForegroundColor Cyan
    Start-Sleep -Seconds 10
}

# Get role ARN
$ROLE_ARN = aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text --region $REGION

# Create or update Lambda function
Write-Host "Deploying Lambda function..." -ForegroundColor Yellow
$functionExists = aws lambda get-function --function-name $FUNCTION_NAME --region $REGION 2>&1
if ($LASTEXITCODE -eq 0) {
    aws lambda update-function-code --function-name $FUNCTION_NAME --zip-file $S3_KEY --region $REGION
    aws lambda update-function-configuration --function-name $FUNCTION_NAME --role $ROLE_ARN --timeout 30 --region $REGION
} else {
    aws lambda create-function `
        --function-name $FUNCTION_NAME `
        --runtime python3.12 `
        --role $ROLE_ARN `
        --handler lambda_function.lambda_handler `
        --zip-file $S3_KEY `
        --timeout 30 `
        --region $REGION
}

# Set environment variables (example - you should customize these)
Write-Host "Setting environment variables..." -ForegroundColor Yellow
$account = aws sts get-caller-identity --query Account --output text
aws lambda update-function-configuration `
    --function-name $FUNCTION_NAME `
    --environment Variables="{
        POWERSCALE_HOST='your-cluster.example.com',
        POWERSCALE_USERNAME='admin',
        POWERSCALE_PASSWORD='your-password',
        POWERSCALE_PORT='8080',
        POWERSCALE_SSL_VERIFY='false',
        SNS_TOPIC_ARN='arn:aws:sns:$REGION`:$account`:your-topic-name',
        CRITICAL_THRESHOLD='50',
        DEGRADED_THRESHOLD='80'
    }" `
    --region $REGION

# Clean up
Write-Host "Cleaning up..." -ForegroundColor Yellow
Remove-Item -Recurse -Force package
Remove-Item -Force deployment.zip

Write-Host "Deployment complete!" -ForegroundColor Green
Write-Host "Function ARN: aws lambda get-function --function-name $FUNCTION_NAME --query 'Configuration.FunctionArn' --output text --region $REGION" -ForegroundColor Cyan
