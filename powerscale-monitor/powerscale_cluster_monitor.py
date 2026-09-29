#!/usr/bin/env python3
"""
PowerScale Cluster Status Monitor

This script monitors PowerScale cluster status using the OneFS REST API,
including cluster configuration, unresolved events, and node statistics.
"""

import json
import logging
import os
import requests
import urllib3
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
import argparse
import sys
import getpass
from pathlib import Path
import yaml
import time
from functools import wraps

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Cluster health status levels."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"


@dataclass
class ClusterConfig:
    """Cluster configuration data."""

    name: str
    onefs_version: str
    build: str
    has_quorum: bool
    is_virtual: bool
    is_vonefs: bool
    join_mode: str
    timezone: str
    devices: List[Dict[str, Any]]


@dataclass
class EventInfo:
    """Event information structure."""

    id: str
    causes: List
    event_count: int
    time_noticed: Optional[int]
    specifier: Dict[str, Any]


@dataclass
class EventsAnalysis:
    """Analysis of cluster events."""

    total: int
    critical: List[EventInfo]
    warning: List[EventInfo]
    information: List[EventInfo]
    by_category: Dict[str, List[EventInfo]]


class PowerScaleAPIError(Exception):
    """Base exception for PowerScale API errors."""

    pass


class AuthenticationError(PowerScaleAPIError):
    """Authentication failed."""

    pass


class ConnectionError(PowerScaleAPIError):
    """Connection to cluster failed."""

    pass


class APIRequestError(PowerScaleAPIError):
    """API request failed."""

    pass


# Constants
DEFAULT_PORT = 8080
DEFAULT_TIMEOUT = 30
HEALTH_SCORE_CRITICAL_THRESHOLD = 50
HEALTH_SCORE_DEGRADED_THRESHOLD = 80
CRITICAL_EVENT_PENALTY = 20
WARNING_EVENT_PENALTY = 5
DEFAULT_STAT_KEYS = ["node.cpu.idle.avg", "node.disk.busy.avg"]
FALLBACK_STAT_KEYS = "node.cpu.idle.avg,node.disk.busy.avg"
DEFAULT_CONFIG_FILE = "powerscale_config.yaml"
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


def retry_on_failure(max_retries: int = MAX_RETRIES, delay: int = RETRY_DELAY):
    """Decorator to retry function on failure.

    Args:
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (requests.exceptions.RequestException, PowerScaleAPIError) as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed")
            raise last_exception

        return wrapper

    return decorator


def load_config_file(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from YAML file.

    Args:
        config_path: Path to config file. If None, checks default locations.

    Returns:
        Dictionary with configuration values
    """
    if config_path:
        config_file = Path(config_path)
    else:
        # Check default locations
        for location in [
            DEFAULT_CONFIG_FILE,
            f".{DEFAULT_CONFIG_FILE}",
            f"~/.{DEFAULT_CONFIG_FILE}",
            f"~/.config/powerscale/{DEFAULT_CONFIG_FILE}",
        ]:
            config_file = Path(location).expanduser()
            if config_file.exists():
                break
        else:
            return {}

    try:
        with open(config_file, "r") as f:
            config = yaml.safe_load(f) or {}
        logger.info(f"Loaded configuration from {config_file}")
        return config
    except (IOError, yaml.YAMLError) as e:
        logger.warning(f"Could not load config file {config_file}: {e}")
        return {}


class PowerScaleClusterMonitor:
    """Monitor PowerScale cluster status and health."""

    def __init__(
        self,
        host: str,
        port: int = DEFAULT_PORT,
        username: str = None,
        password: str = None,
        verify_ssl: bool = False,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        """Initialize the cluster monitor.

        Args:
            host: PowerScale cluster hostname or IP
            port: API port (default: 8080)
            username: API username
            password: API password
            verify_ssl: Enable SSL verification (default: False)
            timeout: Request timeout in seconds (default: 30)
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.base_url = f"https://{host}:{port}"
        self.session = None

        if not all([host, username, password]):
            raise ValueError("host, username, and password are required")

        logger.info(f"Initializing monitor for {self.base_url}")

    def init_session(self) -> None:
        """Initialize API session with authentication and timeout settings."""
        try:
            self.session = requests.Session()
            self.session.auth = (self.username, self.password)
            self.session.verify = self.verify_ssl
            self.session.timeout = self.timeout
            logger.debug("API session initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize session: {e}")
            raise ConnectionError(f"Session initialization failed: {e}")

    @retry_on_failure()
    def get_cluster_config(self) -> Dict[str, Any]:
        """Get cluster configuration and status.

        Returns:
            Dictionary containing cluster configuration data

        Raises:
            APIRequestError: If the API request fails
        """
        try:
            logger.debug("Fetching cluster configuration")
            response = self.session.get(f"{self.base_url}/platform/17/cluster/config")
            response.raise_for_status()
            config = response.json()
            logger.info("Successfully retrieved cluster configuration")
            return config
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.error("Authentication failed")
                raise AuthenticationError("Invalid credentials")
            logger.error(f"HTTP error fetching cluster config: {e}")
            raise APIRequestError(f"HTTP error: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting cluster config: {e}")
            raise APIRequestError(f"Request failed: {e}")

    @retry_on_failure()
    def get_unresolved_events(self) -> Dict[str, Any]:
        """Get unresolved events from the cluster.

        Returns:
            Dictionary containing unresolved events data

        Raises:
            APIRequestError: If the API request fails
        """
        try:
            logger.debug("Fetching unresolved events")
            response = self.session.get(
                f"{self.base_url}/platform/12/event/eventgroup-occurrences",
                params={"resolved": "false"},
            )
            response.raise_for_status()
            events = response.json()
            logger.info(f"Retrieved {events.get('total', 0)} unresolved events")
            return events
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting unresolved events: {e}")
            raise APIRequestError(f"Failed to fetch events: {e}")

    @retry_on_failure()
    def get_node_statistics(self, keys: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get current node statistics.

        Args:
            keys: List of statistic keys to retrieve. If None, uses default keys.

        Returns:
            Dictionary containing node statistics data

        Raises:
            APIRequestError: If the API request fails
        """
        if keys is None:
            keys = DEFAULT_STAT_KEYS

        try:
            logger.debug(f"Fetching node statistics for keys: {keys}")
            response = self.session.get(
                f"{self.base_url}/platform/1/statistics/current",
                params={"keys": ",".join(keys), "nodes": "all"},
            )
            response.raise_for_status()
            stats = response.json()
            logger.info("Successfully retrieved node statistics")
            return stats
        except requests.exceptions.RequestException as e:
            logger.warning(f"Error getting node statistics with custom keys: {e}")
            # Try with fallback keys
            try:
                logger.debug("Attempting fallback with default keys")
                response = self.session.get(
                    f"{self.base_url}/platform/1/statistics/current",
                    params={"keys": FALLBACK_STAT_KEYS, "nodes": "all"},
                )
                response.raise_for_status()
                stats = response.json()
                logger.info("Successfully retrieved node statistics with fallback keys")
                return stats
            except requests.exceptions.RequestException as e2:
                logger.error(f"Error getting node statistics with fallback: {e2}")
                raise APIRequestError(f"Failed to fetch statistics: {e2}")

    def analyze_events(self, events_data: Dict[str, Any]) -> EventsAnalysis:
        """Analyze events and categorize by severity.

        Args:
            events_data: Raw events data from API

        Returns:
            EventsAnalysis object with categorized events
        """
        analysis = EventsAnalysis(
            total=0, critical=[], warning=[], information=[], by_category={}
        )

        if "eventgroups" not in events_data:
            logger.warning("No eventgroups found in events data")
            return analysis

        analysis.total = events_data.get("total", 0)
        logger.debug(f"Analyzing {analysis.total} events")

        for event in events_data["eventgroups"]:
            severity = event.get("severity", "unknown")
            event_info = EventInfo(
                id=event.get("id", ""),
                causes=event.get("causes", []),
                event_count=event.get("event_count", 0),
                time_noticed=event.get("time_noticed"),
                specifier=event.get("specifier", {}),
            )

            if severity == "critical":
                analysis.critical.append(event_info)
            elif severity == "warning":
                analysis.warning.append(event_info)
            elif severity == "information":
                analysis.information.append(event_info)

            # Categorize by cause
            for cause in event.get("causes", []):
                if isinstance(cause, list) and len(cause) >= 2:
                    category = cause[0]
                    if category not in analysis.by_category:
                        analysis.by_category[category] = []
                    analysis.by_category[category].append(event_info)

        logger.info(
            f"Event analysis complete: {len(analysis.critical)} critical, "
            f"{len(analysis.warning)} warning, {len(analysis.information)} info"
        )
        return analysis

    def format_timestamp(self, timestamp: Optional[int]) -> str:
        """Format Unix timestamp to readable string.

        Args:
            timestamp: Unix timestamp or None

        Returns:
            Formatted datetime string or "N/A"
        """
        if timestamp:
            return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        return "N/A"

    def print_cluster_summary(self, config: Dict[str, Any]) -> None:
        """Print cluster configuration summary.

        Args:
            config: Cluster configuration dictionary
        """
        print("\n" + "=" * 60)
        print("CLUSTER CONFIGURATION")
        print("=" * 60)

        if not config:
            logger.warning("No cluster configuration data available")
            print("No cluster configuration data available")
            return

        print(f"Cluster Name: {config.get('name', 'Unknown')}")
        print(
            f"OneFS Version: {config.get('onefs_version', {}).get('version', 'Unknown')}"
        )
        print(f"Build: {config.get('onefs_version', {}).get('build', 'Unknown')}")
        print(f"Has Quorum: {config.get('has_quorum', False)}")
        print(f"Is Virtual: {config.get('is_virtual', False)}")
        print(f"Is VOneFS: {config.get('is_vonefs', False)}")
        print(f"Join Mode: {config.get('join_mode', 'Unknown')}")
        print(f"Timezone: {config.get('timezone', {}).get('name', 'Unknown')}")

        devices = config.get("devices", [])
        if devices:
            print(f"\nNodes: {len(devices)}")
            for device in devices:
                status = "UP" if device.get("is_up") else "DOWN"
                print(
                    f"  - Node {device.get('lnn')}: Device ID {device.get('devid')} ({status})"
                )

    def print_events_summary(self, events_analysis: EventsAnalysis) -> None:
        """Print events analysis summary.

        Args:
            events_analysis: EventsAnalysis object with categorized events
        """
        print("\n" + "=" * 60)
        print("UNRESOLVED EVENTS SUMMARY")
        print("=" * 60)

        print(f"Total Unresolved Events: {events_analysis.total}")
        print(f"Critical: {len(events_analysis.critical)}")
        print(f"Warning: {len(events_analysis.warning)}")
        print(f"Information: {len(events_analysis.information)}")

        if events_analysis.critical:
            print("\n[CRITICAL] CRITICAL EVENTS:")
            for event in events_analysis.critical:
                print(f"\n  Event ID: {event.id} (Count: {event.event_count})")
                print(f"  Time: {self.format_timestamp(event.time_noticed)}")
                for cause in event.causes:
                    if isinstance(cause, list) and len(cause) >= 2:
                        print(f"  - {cause[0]}: {cause[1]}")

        if events_analysis.warning:
            print("\n[WARNING] WARNING EVENTS:")
            for event in events_analysis.warning:
                print(f"\n  Event ID: {event.id} (Count: {event.event_count})")
                print(f"  Time: {self.format_timestamp(event.time_noticed)}")
                for cause in event.causes:
                    if isinstance(cause, list) and len(cause) >= 2:
                        print(f"  - {cause[0]}: {cause[1]}")

        if events_analysis.by_category:
            print("\n[INFO] EVENTS BY CATEGORY:")
            for category, events in events_analysis.by_category.items():
                total_count = sum(e.event_count for e in events)
                print(
                    f"  {category}: {total_count} events ({len(events)} event groups)"
                )

    def print_statistics_summary(self, stats_data: Dict[str, Any]) -> None:
        """Print node statistics summary.

        Args:
            stats_data: Statistics data from API
        """
        print("\n" + "=" * 60)
        print("NODE STATISTICS")
        print("=" * 60)

        if "stats" not in stats_data:
            logger.warning("No statistics data available")
            print("No statistics data available")
            return

        # Group by device
        devices: Dict[str, Dict[str, Any]] = {}
        for stat in stats_data["stats"]:
            devid = stat.get("devid")
            if devid not in devices:
                devices[devid] = {}
            devices[devid][stat.get("key")] = stat.get("value")

        for devid, metrics in devices.items():
            print(f"\nDevice {devid}:")
            for key, value in metrics.items():
                # Format values based on key type
                if "cpu" in key and "idle" in key:
                    print(f"  {key}: {value/10:.1f}%")
                elif "disk" in key and "busy" in key:
                    print(f"  {key}: {value/10:.1f}%")
                elif "memory" in key:
                    print(f"  {key}: {value}")
                else:
                    print(f"  {key}: {value}")

    def generate_health_score(self, events_analysis: EventsAnalysis) -> int:
        """Generate a simple health score (0-100).

        Args:
            events_analysis: EventsAnalysis object with categorized events

        Returns:
            Health score from 0-100
        """
        score = 100

        # Deduct points for critical events
        score -= len(events_analysis.critical) * CRITICAL_EVENT_PENALTY

        # Deduct points for warnings
        score -= len(events_analysis.warning) * WARNING_EVENT_PENALTY

        # Ensure score doesn't go below 0
        return max(0, score)

    def print_health_summary(self, events_analysis: EventsAnalysis) -> None:
        """Print overall cluster health summary.

        Args:
            events_analysis: EventsAnalysis object with categorized events
        """
        print("\n" + "=" * 60)
        print("CLUSTER HEALTH SUMMARY")
        print("=" * 60)

        health_score = self.generate_health_score(events_analysis)

        if health_score >= HEALTH_SCORE_DEGRADED_THRESHOLD:
            status = f"[OK] {HealthStatus.HEALTHY.value}"
        elif health_score >= HEALTH_SCORE_CRITICAL_THRESHOLD:
            status = f"[WARN] {HealthStatus.DEGRADED.value}"
        else:
            status = f"[CRITICAL] {HealthStatus.CRITICAL.value}"

        print(f"Health Score: {health_score}/100 - {status}")
        print(f"Active Issues: {events_analysis.total}")

        if health_score < HEALTH_SCORE_DEGRADED_THRESHOLD:
            print("\nRecommendations:")
            if events_analysis.critical:
                print("- Address critical events immediately")
            if events_analysis.warning:
                print("- Review and resolve warning events")
            print("- Monitor cluster performance closely")

    def save_report(self, report_data: Dict[str, Any], filename: str) -> None:
        """Save the complete report to a JSON file.

        Args:
            report_data: Dictionary containing all report data
            filename: Path to save the report file
        """
        try:
            report_path = Path(filename)
            report_path.parent.mkdir(parents=True, exist_ok=True)

            with open(report_path, "w") as f:
                json.dump(report_data, f, indent=2, default=str)
            logger.info(f"Report saved to: {filename}")
            print(f"\n[REPORT] Report saved to: {filename}")
        except (IOError, OSError) as e:
            logger.error(f"Error saving report: {e}")
            print(f"Error saving report: {e}")

    def run_monitoring(
        self, save_report: bool = False, report_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """Run complete cluster monitoring.

        Args:
            save_report: Whether to save report to JSON file
            report_filename: Custom report filename (auto-generated if None)

        Returns:
            Dictionary containing monitoring results
        """
        print("=" * 60)
        print("POWERSCALE CLUSTER STATUS MONITOR")
        print("=" * 60)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Cluster: {self.host}:{self.port}")

        # Initialize session
        self.init_session()

        # Collect data
        cluster_config = self.get_cluster_config()
        events_data = self.get_unresolved_events()
        stats_data = self.get_node_statistics()

        # Analyze events
        events_analysis = self.analyze_events(events_data)

        # Print summaries
        self.print_cluster_summary(cluster_config)
        self.print_events_summary(events_analysis)
        self.print_statistics_summary(stats_data)
        self.print_health_summary(events_analysis)

        # Save report if requested
        if save_report:
            if not report_filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                report_filename = f"cluster_status_report_{timestamp}.json"

            report_data = {
                "timestamp": datetime.now().isoformat(),
                "cluster_config": cluster_config,
                "events_data": events_data,
                "events_analysis": {
                    "total": events_analysis.total,
                    "critical": [
                        {
                            "id": e.id,
                            "causes": e.causes,
                            "event_count": e.event_count,
                            "time_noticed": e.time_noticed,
                            "specifier": e.specifier,
                        }
                        for e in events_analysis.critical
                    ],
                    "warning": [
                        {
                            "id": e.id,
                            "causes": e.causes,
                            "event_count": e.event_count,
                            "time_noticed": e.time_noticed,
                            "specifier": e.specifier,
                        }
                        for e in events_analysis.warning
                    ],
                    "information": [
                        {
                            "id": e.id,
                            "causes": e.causes,
                            "event_count": e.event_count,
                            "time_noticed": e.time_noticed,
                            "specifier": e.specifier,
                        }
                        for e in events_analysis.information
                    ],
                    "by_category": {
                        k: [
                            {
                                "id": e.id,
                                "causes": e.causes,
                                "event_count": e.event_count,
                                "time_noticed": e.time_noticed,
                                "specifier": e.specifier,
                            }
                            for e in v
                        ]
                        for k, v in events_analysis.by_category.items()
                    },
                },
                "statistics": stats_data,
                "health_score": self.generate_health_score(events_analysis),
            }

            self.save_report(report_data, report_filename)

        return {
            "cluster_config": cluster_config,
            "events_analysis": events_analysis,
            "statistics": stats_data,
            "health_score": self.generate_health_score(events_analysis),
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Monitor PowerScale cluster status using the OneFS REST API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (prompts for credentials)
  python powerscale_cluster_monitor.py
  
  # Command line with credentials
  python powerscale_cluster_monitor.py --host 192.168.1.50 --username root --password secret
  
  # Using environment variables
  export POWERSCALE_HOST=192.168.1.50
  export POWERSCALE_USERNAME=root
  export POWERSCALE_PASSWORD=secret
  python powerscale_cluster_monitor.py
  
  # Save report to file
  python powerscale_cluster_monitor.py --save-report --report-file my_report.json
        """,
    )
    parser.add_argument("--host", help="PowerScale cluster host (env: POWERSCALE_HOST)")
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"API port (default: {DEFAULT_PORT}, env: POWERSCALE_PORT)",
    )
    parser.add_argument("--username", help="API username (env: POWERSCALE_USERNAME)")
    parser.add_argument("--password", help="API password (env: POWERSCALE_PASSWORD)")
    parser.add_argument(
        "--ssl-verify",
        action="store_true",
        help="Enable SSL verification (disabled by default, env: POWERSCALE_SSL_VERIFY)",
    )
    parser.add_argument(
        "--save-report",
        action="store_true",
        help="Save report to JSON file (env: POWERSCALE_SAVE_REPORT)",
    )
    parser.add_argument(
        "--report-file", help="Custom report filename (env: POWERSCALE_REPORT_FILE)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Request timeout in seconds (default: {DEFAULT_TIMEOUT}, env: POWERSCALE_TIMEOUT)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument("--config", "-c", help="Path to configuration file (YAML)")

    args = parser.parse_args()

    # Load configuration file if specified
    config = load_config_file(args.config)

    # Set logging level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Get credentials from config file, environment variables, or command line
    host = args.host or config.get("host") or os.getenv("POWERSCALE_HOST")
    port = (
        args.port
        or config.get("port", DEFAULT_PORT)
        or int(os.getenv("POWERSCALE_PORT", DEFAULT_PORT))
    )
    username = (
        args.username or config.get("username") or os.getenv("POWERSCALE_USERNAME")
    )
    password = (
        args.password or config.get("password") or os.getenv("POWERSCALE_PASSWORD")
    )
    ssl_verify = (
        args.ssl_verify
        or config.get("ssl_verify", False)
        or os.getenv("POWERSCALE_SSL_VERIFY", "").lower() == "true"
    )
    save_report = (
        args.save_report
        or config.get("save_report", False)
        or os.getenv("POWERSCALE_SAVE_REPORT", "").lower() == "true"
    )
    report_file = (
        args.report_file
        or config.get("report_file")
        or os.getenv("POWERSCALE_REPORT_FILE")
    )
    timeout = (
        args.timeout
        or config.get("timeout", DEFAULT_TIMEOUT)
        or int(os.getenv("POWERSCALE_TIMEOUT", DEFAULT_TIMEOUT))
    )

    # Prompt for credentials if not provided
    if not host:
        host = input("Enter PowerScale cluster host: ")
    if not username:
        username = input("Enter API username: ")
    if not password:
        password = getpass.getpass("Enter API password: ")

    try:
        monitor = PowerScaleClusterMonitor(
            host=host,
            port=port,
            username=username,
            password=password,
            verify_ssl=ssl_verify,
            timeout=timeout,
        )
    except ValueError as e:
        logger.error(f"Invalid configuration: {e}")
        sys.exit(1)

    try:
        results = monitor.run_monitoring(
            save_report=save_report, report_filename=report_file
        )

        # Exit with error code based on health score
        health_score = results["health_score"]
        if health_score < HEALTH_SCORE_CRITICAL_THRESHOLD:
            logger.warning(f"Cluster health critical: {health_score}/100")
            sys.exit(2)
        elif health_score < HEALTH_SCORE_DEGRADED_THRESHOLD:
            logger.warning(f"Cluster health degraded: {health_score}/100")
            sys.exit(1)
        else:
            logger.info(f"Cluster health OK: {health_score}/100")
            sys.exit(0)

    except AuthenticationError as e:
        logger.error(f"Authentication failed: {e}")
        sys.exit(4)
    except ConnectionError as e:
        logger.error(f"Connection failed: {e}")
        sys.exit(5)
    except APIRequestError as e:
        logger.error(f"API request failed: {e}")
        sys.exit(6)
    except KeyboardInterrupt:
        logger.info("Monitoring interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error during monitoring: {e}")
        sys.exit(3)


if __name__ == "__main__":
    main()
