#!/bin/bash
# Deployment script for PowerScale Cloud Monitor Lambda function

set -e

# Configuration
FUNCTION_NAME="powerscale-monitor"
ROLE_NAME="powerscale-monitor-role"
S3_BUCKET="${S3_BUCKET:-your-deployment-bucket}"
REGION="${AWS_REGION:-us-east-1}"

echo "Deploying PowerScale Cloud Monitor..."

# Create deployment package
echo "Creating deployment package..."
mkdir -p package
cp lambda_function.py package/
cd package
pip install -r ../requirements.txt -t .
cd ..
zip -r deployment.zip package/*

# Upload to S3 (optional)
if [ -n "$S3_BUCKET" ]; then
    echo "Uploading to S3..."
    aws s3 cp deployment.zip s3://$S3_BUCKET/powerscale-monitor/deployment.zip
    S3_KEY="s3://$S3_BUCKET/powerscale-monitor/deployment.zip"
else
    S3_KEY="fileb://deployment.zip"
fi

# Create IAM role if it doesn't exist
echo "Setting up IAM role..."
if ! aws iam get-role --role-name $ROLE_NAME --region $REGION 2>/dev/null; then
    aws iam create-role --role-name $ROLE_NAME --assume-role-policy-document file://iam-trust-policy.json --region $REGION
    aws iam put-role-policy --role-name $ROLE_NAME --policy-name PowerScaleMonitorPolicy --policy-document file://iam-policy.json --region $REGION
    echo "Waiting for role to propagate..."
    sleep 10
fi

# Get role ARN
ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text --region $REGION)

# Create or update Lambda function
echo "Deploying Lambda function..."
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION 2>/dev/null; then
    aws lambda update-function-code --function-name $FUNCTION_NAME --zip-file $S3_KEY --region $REGION
    aws lambda update-function-configuration --function-name $FUNCTION_NAME --role $ROLE_ARN --timeout 30 --region $REGION
else
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime python3.9 \
        --role $ROLE_ARN \
        --handler lambda_function.lambda_handler \
        --zip-file $S3_KEY \
        --timeout 30 \
        --region $REGION
fi

# Set environment variables (example - you should customize these)
echo "Setting environment variables..."
aws lambda update-function-configuration \
    --function-name $FUNCTION_NAME \
    --environment Variables={
        POWERSCALE_HOST="your-cluster.example.com",
        POWERSCALE_USERNAME="admin",
        POWERSCALE_PASSWORD="your-password",
        POWERSCALE_PORT="8080",
        POWERSCALE_SSL_VERIFY="false",
        SNS_TOPIC_ARN="arn:aws:sns:$REGION:$(aws sts get-caller-identity --query Account --output text):your-topic-name",
        CRITICAL_THRESHOLD="50",
        DEGRADED_THRESHOLD="80"
    } \
    --region $REGION

# Clean up
echo "Cleaning up..."
rm -rf package deployment.zip

echo "Deployment complete!"
echo "Function ARN: aws lambda get-function --function-name $FUNCTION_NAME --query 'Configuration.FunctionArn' --output text --region $REGION"
