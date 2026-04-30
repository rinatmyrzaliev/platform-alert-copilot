import logging
from fastapi import FastAPI
from src.models import WebhookPayload
from src.enricher import enrich_alert
from src.triage import call_claude

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("alert-copilot")

app = FastAPI(title="Alert Copilot")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/webhook")
def webhook(payload: WebhookPayload):
    results = []
    for alert in payload.alerts:
        if alert.status != "firing":
            continue

        logger.info(
            "Alert received: name=%s namespace=%s service=%s severity=%s summary=%s",
            alert.labels.get("alertname", "unknown"),
            alert.labels.get("namespace", "unknown"),
            alert.labels.get("service", "unknown"),
            alert.labels.get("severity", "unknown"),
            alert.annotations.get("summary", "no summary"),
        )
        
        context = enrich_alert(alert)
        triage = call_claude(context)
        logger.info("Triage result:\n%s", triage)
        
        results.append({
            "context": context,
            "triage": triage,
        })

    return {"status": "accepted", "alerts_processed": len(results), "contexts": results}