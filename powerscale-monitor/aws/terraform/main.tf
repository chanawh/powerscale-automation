terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# SNS Topic for alerts
resource "aws_sns_topic" "powerscale_alerts" {
  name = "powerscale-cluster-alerts"
}

# SNS Topic Subscription (email)
resource "aws_sns_topic_subscription" "email_alerts" {
  count                           = length(var.alert_emails) > 0 ? 1 : 0
  topic_arn                       = aws_sns_topic.powerscale_alerts.arn
  protocol                        = "email"
  endpoint                        = var.alert_emails[0]
  confirmation_timeout_in_minutes = 10
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "powerscale-monitor-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# IAM Policy for Lambda
resource "aws_iam_role_policy" "lambda_policy" {
  name = "powerscale-monitor-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.powerscale_alerts.arn
      }
    ]
  })
}

# Lambda Function
resource "aws_lambda_function" "powerscale_monitor" {
  filename         = "../deployment.zip"
  function_name    = "powerscale-monitor"
  role            = aws_iam_role.lambda_role.arn
  handler         = "lambda_function.lambda_handler"
  runtime         = "python3.12"
  timeout         = 30
  source_code_hash = filebase64sha256("../deployment.zip")

  environment {
    variables = {
      POWERSCALE_HOST       = var.powerscale_host
      POWERSCALE_USERNAME  = var.powerscale_username
      POWERSCALE_PASSWORD  = var.powerscale_password
      POWERSCALE_PORT      = var.powerscale_port
      POWERSCALE_SSL_VERIFY = var.powerscale_ssl_verify
      SNS_TOPIC_ARN        = aws_sns_topic.powerscale_alerts.arn
      CRITICAL_THRESHOLD   = var.critical_threshold
      DEGRADED_THRESHOLD   = var.degraded_threshold
      CLOUDWATCH_NAMESPACE = var.cloudwatch_namespace
    }
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/powerscale-monitor"
  retention_in_days = 7
}

# EventBridge Rule (Schedule)
resource "aws_cloudwatch_event_rule" "monitoring_schedule" {
  name                = "powerscale-monitoring-schedule"
  description         = "Schedule PowerScale monitoring"
  schedule_expression = var.schedule_expression
}

# EventBridge Target
resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.monitoring_schedule.name
  target_id = "powerscale-monitor"
  arn       = aws_lambda_function.powerscale_monitor.arn
}

# Lambda Permission for EventBridge
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.powerscale_monitor.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.monitoring_schedule.arn
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "health_score_critical" {
  alarm_name          = "powerscale-health-score-critical"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "HealthScore"
  namespace           = var.cloudwatch_namespace
  period              = "300"
  statistic           = "Average"
  threshold           = var.critical_threshold
  alarm_description   = "This metric monitors PowerScale cluster health score"
  alarm_actions       = [aws_sns_topic.powerscale_alerts.arn]
  dimensions = {
    Cluster = var.powerscale_host
  }
}

resource "aws_cloudwatch_metric_alarm" "health_score_degraded" {
  alarm_name          = "powerscale-health-score-degraded"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "HealthScore"
  namespace           = var.cloudwatch_namespace
  period              = "300"
  statistic           = "Average"
  threshold           = var.degraded_threshold
  alarm_description   = "This metric monitors PowerScale cluster health score"
  alarm_actions       = [aws_sns_topic.powerscale_alerts.arn]
  dimensions = {
    Cluster = var.powerscale_host
  }
}

resource "aws_cloudwatch_metric_alarm" "node_down" {
  alarm_name          = "powerscale-node-down"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "DownNodes"
  namespace           = var.cloudwatch_namespace
  period              = "300"
  statistic           = "Average"
  threshold           = "0"
  alarm_description   = "This metric monitors PowerScale cluster node status"
  alarm_actions       = [aws_sns_topic.powerscale_alerts.arn]
  dimensions = {
    Cluster = var.powerscale_host
  }
}

# CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "powerscale" {
  dashboard_name = "PowerScale-Cluster-Monitor"
  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["PowerScale/Cluster", "HealthScore"],
            ["PowerScale/Cluster", "TotalNodes"],
            ["PowerScale/Cluster", "UpNodes"],
            ["PowerScale/Cluster", "DownNodes"]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "PowerScale Cluster Health"
        }
      }
    ]
  })
}

# Outputs
output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.powerscale_monitor.arn
}

output "sns_topic_arn" {
  description = "ARN of the SNS topic for alerts"
  value       = aws_sns_topic.powerscale_alerts.arn
}

output "cloudwatch_dashboard_link" {
  description = "Link to CloudWatch console"
  value       = "https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#metricsV2:namespace=${var.cloudwatch_namespace}"
}
