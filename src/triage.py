import os
import logging
import httpx

logger = logging.getLogger("alert-copilot")

CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"

SYSTEM_PROMPT = """You are an experienced SRE on-call engineer. You receive alerts with live metrics from Prometheus.

Your job is to provide a short triage summary with:
1. Likely root cause (based on the alert and metrics)
2. What to check first (specific commands or dashboards)
3. Suggested actions (what to do to fix or mitigate)

Keep it short and actionable. No long explanations. The on-call engineer is being paged at 3am and needs clear next steps."""


def build_user_message(context: dict) -> str:
    alert = context["alert"]
    metrics = context["metrics"]

    return f"""ALERT FIRED:
- Name: {alert['name']}
- Namespace: {alert['namespace']}
- Service: {alert['service']}
- Severity: {alert['severity']}
- Summary: {alert['summary']}
- Started at: {alert['started_at']}
- Runbook: {alert['runbook_url']}

CURRENT METRICS:
- Error rate (5xx): {metrics['error_rate_5xx']}
- Latency p99: {metrics['latency_p99']}
- Pod count: {metrics['pod_count']}
- Pod restarts (last 10m): {metrics['pod_restarts']}

Provide your triage summary."""


def call_claude(context: dict) -> str:
    api_key = os.environ.get("claude-api-key", "")
    if not api_key:
        logger.error("CLAUDE_API_KEY not set")
        return "Triage unavailable: no API key configured"

    user_message = build_user_message(context)

    try:
        response = httpx.post(
            CLAUDE_API_URL,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 1024,
                "system": SYSTEM_PROMPT,
                "messages": [
                    {"role": "user", "content": user_message}
                ],
            },
            timeout=30.0,
        )

        data = response.json()
        if "content" in data:
            return data["content"][0]["text"]
        else:
            logger.error("Claude API error: %s", data)
            return f"Triage failed: {data.get('error', {}).get('message', 'unknown error')}"

    except Exception as e:
        logger.error("Claude API call failed: %s", e)
        return f"Triage unavailable: {str(e)}"