#!/bin/bash
# Build script for creating Lambda deployment package

set -e

echo "Building Lambda deployment package..."

# Clean up previous builds
rm -rf package deployment.zip

# Create package directory
mkdir -p package

# Copy Lambda function
cp lambda_function.py package/

# Install dependencies
echo "Installing dependencies..."
cd package
pip install -r ../aws-requirements.txt -t .
cd ..

# Create zip file
echo "Creating deployment package..."
zip -r deployment.zip package/*

# Clean up package directory
rm -rf package

echo "Build complete! deployment.zip created."
echo "Size: $(du -h deployment.zip | cut -f1)"
