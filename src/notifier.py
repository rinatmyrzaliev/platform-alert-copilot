import logging
import httpx

logger = logging.getLogger("alert-copilot")

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1499457301499875358/5Nk_fjGxYxFvjZpIwJw4TdEMO5EH6eCy4tw3yc_BbdvvZ8oIBbTAsbhDIPxlI6qqVh7v"


def send_to_discord(context: dict, triage: str):
    alert = context["alert"]
    metrics = context["metrics"]

    message = (
        f"**Alert: {alert['name']}**\n"
        f"Namespace: {alert['namespace']} | Service: {alert['service']} | Severity: {alert['severity']}\n"
        f"Summary: {alert['summary']}\n\n"
        f"**Metrics:**\n"
        f"- Error rate: {metrics['error_rate_5xx']}\n"
        f"- Latency p99: {metrics['latency_p99']}\n"
        f"- Pod count: {metrics['pod_count']}\n"
        f"- Restarts: {metrics['pod_restarts']}\n\n"
        f"**Triage:**\n{triage}"
    )

    # Discord limit is 2000 characters
    if len(message) > 2000:
        message = message[:1997] + "..."

    try:
        response = httpx.post(
            DISCORD_WEBHOOK_URL,
            json={"content": message},
            timeout=5.0,
        )
        logger.info("Discord notification sent: %s", response.status_code)
    except Exception as e:
        logger.warning("Discord notification failed: %s", e)