import logging
import httpx

logger = logging.getLogger("alert-copilot")

PROMETHEUS_URL = "http://kube-prometheus-stack-prometheus.monitoring.svc.cluster.local:9090"


def query_prometheus(promql: str) -> str:
    try:
        response = httpx.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": promql},
            timeout=5.0,
        )
        data = response.json()
        if data["status"] == "success" and data["data"]["result"]:
            return data["data"]["result"][0]["value"][1]
        return "no data"
    except Exception as e:
        logger.warning("Prometheus query failed: %s", e)
        return "query failed"
    

def enrich_alert(alert) -> dict:
    namespace = alert.labels.get("namespace", "unknown")
    service = alert.labels.get("service", "unknown")

    context = {
        "alert": {
            "name": alert.labels.get("alertname", "unknown"),
            "namespace": namespace,
            "service": service,
            "severity": alert.labels.get("severity", "unknown"),
            "summary": alert.annotations.get("summary", ""),
            "runbook_url": alert.annotations.get("runbook_url", ""),
            "started_at": str(alert.startsAt),
        },
        "metrics": {
            "error_rate_5xx": query_prometheus(
                f'sum(rate(nginx_ingress_controller_requests{{namespace="{namespace}", status=~"5.."}}[5m])) / sum(rate(nginx_ingress_controller_requests{{namespace="{namespace}"}}[5m]))'
            ),
            "latency_p99": query_prometheus(
                f'histogram_quantile(0.99, sum(rate(nginx_ingress_controller_request_duration_seconds_bucket{{namespace="{namespace}"}}[5m])) by (le))'
            ),
            "pod_count": query_prometheus(
                f'count(kube_pod_info{{namespace="{namespace}"}})'
            ),
            "pod_restarts": query_prometheus(
                f'sum(increase(kube_pod_container_status_restarts_total{{namespace="{namespace}"}}[10m]))'
            ),
        },
    }

    logger.info("Enriched alert %s with metrics: %s", context["alert"]["name"], context["metrics"])
    return context