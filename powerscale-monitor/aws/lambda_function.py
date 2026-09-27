"""
AWS Lambda function for PowerScale cluster monitoring.
Polls PowerScale API and pushes metrics to CloudWatch with SNS alerting.
"""

import json
import logging
import os
import requests
import urllib3
from datetime import datetime
from typing import Dict, List, Optional, Any
try:
    import boto3
except ImportError:
    boto3 = None

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Constants
DEFAULT_PORT = 8080
DEFAULT_TIMEOUT = 30
HEALTH_SCORE_CRITICAL_THRESHOLD = 50
HEALTH_SCORE_DEGRADED_THRESHOLD = 80
CLOUDWATCH_NAMESPACE = "PowerScale/Cluster"


class PowerScaleMonitor:
    """Monitor PowerScale cluster and push metrics to CloudWatch."""

    def __init__(self, event: Dict[str, Any]):
        """Initialize the monitor with environment variables."""
        self.host = os.environ.get('POWERSCALE_HOST')
        self.port = int(os.environ.get('POWERSCALE_PORT', DEFAULT_PORT))
        self.username = os.environ.get('POWERSCALE_USERNAME')
        self.password = os.environ.get('POWERSCALE_PASSWORD')
        self.verify_ssl = os.environ.get('POWERSCALE_SSL_VERIFY', 'false').lower() == 'true'
        self.timeout = int(os.environ.get('POWERSCALE_TIMEOUT', DEFAULT_TIMEOUT))
        
        # CloudWatch settings
        self.namespace = os.environ.get('CLOUDWATCH_NAMESPACE', CLOUDWATCH_NAMESPACE)
        if boto3:
            self.cloudwatch = boto3.client('cloudwatch')
        else:
            self.cloudwatch = None
        
        # SNS settings
        self.sns_topic_arn = os.environ.get('SNS_TOPIC_ARN')
        self.sns = boto3.client('sns') if (boto3 and self.sns_topic_arn) else None
        
        # Alert thresholds
        self.critical_threshold = int(os.environ.get('CRITICAL_THRESHOLD', HEALTH_SCORE_CRITICAL_THRESHOLD))
        self.degraded_threshold = int(os.environ.get('DEGRADED_THRESHOLD', HEALTH_SCORE_DEGRADED_THRESHOLD))
        
        self.base_url = f"https://{self.host}:{self.port}"
        self.session = None
        
        if not all([self.host, self.username, self.password]):
            raise ValueError("POWERSCALE_HOST, POWERSCALE_USERNAME, and POWERSCALE_PASSWORD are required")

    def init_session(self) -> None:
        """Initialize API session."""
        self.session = requests.Session()
        self.session.auth = (self.username, self.password)
        self.session.verify = self.verify_ssl
        self.session.timeout = self.timeout

    def get_cluster_config(self) -> Dict[str, Any]:
        """Get cluster configuration and status."""
        try:
            response = self.session.get(f"{self.base_url}/platform/17/cluster/config")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting cluster config: {e}")
            return {}

    def get_unresolved_events(self) -> Dict[str, Any]:
        """Get unresolved events from the cluster."""
        try:
            response = self.session.get(
                f"{self.base_url}/platform/12/event/eventgroup-occurrences",
                params={"resolved": "false"}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting unresolved events: {e}")
            return {}

    def get_node_statistics(self) -> Dict[str, Any]:
        """Get current node statistics."""
        try:
            response = self.session.get(
                f"{self.base_url}/platform/1/statistics/current",
                params={"keys": "node.cpu.idle.avg,node.disk.busy.avg", "nodes": "all"}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting node statistics: {e}")
            return {}

    def calculate_health_score(self, events_data: Dict[str, Any]) -> tuple[int, list]:
        """Calculate health score based on events. Returns (score, contributing_events)."""
        score = 100
        contributing = []
        if "eventgroups" in events_data:
            for event in events_data["eventgroups"]:
                severity = event.get("severity", "unknown")
                if severity == "critical":
                    score -= 20
                    contributing.append({
                        "id": event.get("id"),
                        "severity": severity,
                        "causes": event.get("causes", [])
                    })
                elif severity == "warning":
                    score -= 5
                    contributing.append({
                        "id": event.get("id"),
                        "severity": severity,
                        "causes": event.get("causes", [])
                    })
        return max(0, score), contributing

    def put_cloudwatch_metric(self, metric_name: str, value: float, dimensions: List[Dict[str, str]] = None) -> None:
        """Put metric data to CloudWatch."""
        if not self.cloudwatch:
            logger.debug("CloudWatch client not available in this environment; skipping metric publish.")
            return
        try:
            if dimensions is None:
                dimensions = [{"Name": "Cluster", "Value": self.host}]
            
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[{
                    'MetricName': metric_name,
                    'Value': value,
                    'Dimensions': dimensions,
                    'Timestamp': datetime.now()
                }]
            )
            logger.debug(f"Sent metric {metric_name}: {value}")
        except Exception as e:
            logger.error(f"Error sending metric {metric_name}: {e}")

    def send_sns_alert(self, subject: str, message: str) -> None:
        """Send alert via SNS."""
        if not self.sns or not self.sns_topic_arn:
            logger.warning("SNS not configured, skipping alert")
            return
        
        try:
            self.sns.publish(
                TopicArn=self.sns_topic_arn,
                Subject=subject,
                Message=message,
                MessageStructure='string'
            )
            logger.info(f"Sent SNS alert: {subject}")
        except Exception as e:
            logger.error(f"Error sending SNS alert: {e}")

    def process_metrics(self, config: Dict, events: Dict, stats: Dict) -> tuple[int, list]:
        """Process and send metrics to CloudWatch. Returns (health_score, contributing_events)."""
        result = self.calculate_health_score(events)
        
        # Unpack health score and contributing events if provided
        if isinstance(result, tuple):
            health_score, contributing = result
        else:
            health_score = result
            contributing = []
        
        # Cluster health metrics
        self.put_cloudwatch_metric("HealthScore", health_score)
        self.put_cloudwatch_metric("UnresolvedEvents", events.get("total", 0))
        self.put_cloudwatch_metric("CriticalEvents", len([e for e in events.get("eventgroups", []) if e.get("severity") == "critical"]))
        self.put_cloudwatch_metric("WarningEvents", len([e for e in events.get("eventgroups", []) if e.get("severity") == "warning"]))
        
        # Node status metrics
        devices = config.get('devices', [])
        if devices:
            up_nodes = sum(1 for d in devices if d.get('is_up'))
            self.put_cloudwatch_metric("TotalNodes", len(devices))
            self.put_cloudwatch_metric("UpNodes", up_nodes)
            self.put_cloudwatch_metric("DownNodes", len(devices) - up_nodes)
        
        # Quorum status
        self.put_cloudwatch_metric("HasQuorum", 1 if config.get('has_quorum') else 0)
        
        # Performance metrics
        if "stats" in stats:
            cpu_values = []
            disk_values = []
            for stat in stats["stats"]:
                key = stat.get("key")
                value = stat.get("value", 0)
                if "cpu" in key and "idle" in key:
                    cpu_values.append(value / 10)  # Convert to percentage
                elif "disk" in key and "busy" in key:
                    disk_values.append(value / 10)  # Convert to percentage
            
            if cpu_values:
                avg_cpu_idle = sum(cpu_values) / len(cpu_values)
                self.put_cloudwatch_metric("AvgCpuIdle", avg_cpu_idle)
                self.put_cloudwatch_metric("AvgCpuUsed", 100 - avg_cpu_idle)
            
            if disk_values:
                avg_disk_busy = sum(disk_values) / len(disk_values)
                self.put_cloudwatch_metric("AvgDiskBusy", avg_disk_busy)
        
        # Return health score and contributing events for richer handling by caller
        return health_score, contributing

    def check_alerts(self, health_score: int, config: Dict, events: Dict) -> None:
        """Check thresholds and send alerts if needed."""
        status = "HEALTHY"
        if health_score < self.critical_threshold:
            status = "CRITICAL"
        elif health_score < self.degraded_threshold:
            status = "DEGRADED"
        
        if status in ["CRITICAL", "DEGRADED"]:
            critical_events = [e for e in events.get("eventgroups", []) if e.get("severity") == "critical"]
            warning_events = [e for e in events.get("eventgroups", []) if e.get("severity") == "warning"]
            
            message = f"""
PowerScale Cluster Alert - {status}
Cluster: {self.host}
Health Score: {health_score}/100
Timestamp: {datetime.now().isoformat()}

Summary:
- Total Unresolved Events: {events.get('total', 0)}
- Critical Events: {len(critical_events)}
- Warning Events: {len(warning_events)}
- Total Nodes: {len(config.get('devices', []))}
- Up Nodes: {sum(1 for d in config.get('devices', []) if d.get('is_up'))}
- Has Quorum: {config.get('has_quorum', False)}

Critical Events:
"""
            for event in critical_events[:5]:  # Limit to first 5
                message += f"- {event.get('id')}: {event.get('causes', [])}\n"
            
            self.send_sns_alert(f"PowerScale {status}: {self.host}", message)

    def run(self) -> Dict[str, Any]:
        """Main monitoring function."""
        logger.info(f"Starting monitoring for {self.host}")
        
        try:
            self.init_session()
            
            # Collect data
            config = self.get_cluster_config()
            events = self.get_unresolved_events()
            stats = self.get_node_statistics()
            
            # Process and send metrics
            health_score, contributing_events = self.process_metrics(config, events, stats)
            
            # Check for alerts
            self.check_alerts(health_score, config, events)
            
            logger.info(f"Monitoring complete. Health score: {health_score}")
            
            # Build a richer response for debugging and verification
            total_nodes = len(config.get('devices', []))
            up_nodes = sum(1 for d in config.get('devices', []) if d.get('is_up'))
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'health_score': health_score,
                    'cluster': self.host,
                    'timestamp': datetime.now().isoformat(),
                    'total_nodes': total_nodes,
                    'up_nodes': up_nodes,
                    'has_quorum': config.get('has_quorum'),
                    'contributing_events': contributing_events,
                })
            }
            
        except Exception as e:
            logger.error(f"Monitoring failed: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': str(e)})
            }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AWS Lambda entry point."""
    try:
        monitor = PowerScaleMonitor(event)
        return monitor.run()
    except Exception as e:
        logger.error(f"Lambda handler error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
