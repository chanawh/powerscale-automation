variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "powerscale_host" {
  description = "PowerScale cluster hostname or IP"
  type        = string
  sensitive   = true
}

variable "powerscale_username" {
  description = "PowerScale API username"
  type        = string
  sensitive   = true
}

variable "powerscale_password" {
  description = "PowerScale API password"
  type        = string
  sensitive   = true
}

variable "powerscale_port" {
  description = "PowerScale API port"
  type        = number
  default     = 8080
}

variable "powerscale_ssl_verify" {
  description = "Enable SSL verification"
  type        = bool
  default     = false
}

variable "alert_emails" {
  description = "List of email addresses for SNS alerts"
  type        = list(string)
  default     = []
}

variable "critical_threshold" {
  description = "Health score threshold for critical alerts"
  type        = number
  default     = 50
}

variable "degraded_threshold" {
  description = "Health score threshold for degraded alerts"
  type        = number
  default     = 80
}

variable "schedule_expression" {
  description = "EventBridge schedule expression (cron or rate)"
  type        = string
  default     = "rate(5 minutes)"
}

variable "cloudwatch_namespace" {
  description = "CloudWatch namespace for metrics"
  type        = string
  default     = "PowerScale/Cluster"
}
