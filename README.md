# Alert Copilot

LLM-powered alert triage service for Kubernetes. Receives Alertmanager webhooks, enriches them with live Prometheus metrics, and produces actionable triage summaries using Claude API.

## What it does

When an alert fires:

1. **Alertmanager** sends a webhook to the copilot
2. **Copilot** queries Prometheus for live metrics (error rate, latency p99, pod count, restarts)
3. **Copilot** sends the alert + metrics to Claude API with a structured triage prompt
4. **Claude** returns a summary: likely root cause, what to check first, suggested actions
5. **Copilot** posts the triage to Discord (Slack in production) and logs it

The goal is to give the on-call engineer a 30-second head start on context gathering — not to replace them.

## Architecture

```
Prometheus ──► Alertmanager ──► Alert Copilot ──► Discord
                                     │                
                                     ▼                
                                Prometheus             
                              (context queries)        
                                     │                
                                     ▼                
                                Claude API             
                              (triage summary)         
```

## Tech stack

- **Python / FastAPI** — webhook receiver and API
- **Pydantic** — request validation for Alertmanager payloads
- **httpx** — HTTP client for Prometheus and Claude API calls
- **Claude Sonnet** — LLM for triage (fast, cheap, good enough for structured tasks)
- **External Secrets Operator** — API key management via AWS Secrets Manager
- **Helm library chart** — deployed via the same golden path as all platform services

## Project structure

```
platform-alert-copilot/
├── src/
│   ├── __init__.py
│   ├── main.py          # FastAPI app, /healthz and /webhook endpoints
│   ├── models.py         # Pydantic models for Alertmanager webhook payload
│   ├── enricher.py       # Prometheus context enrichment
│   ├── triage.py         # Claude API triage prompt and client
│   └── notifier.py       # Discord webhook notifications
├── manifests/
│   ├── alertmanager-config.yaml   # AlertmanagerConfig CRD to route alerts to copilot
│   └── test-alert.yaml            # PrometheusRule for testing the full chain
├── .github/
│   └── workflows/
│       └── ci.yml        # GitHub Actions: build + push to ECR
├── Dockerfile
├── requirements.txt
└── docs/
    └── decisions.md      # Architecture Decision Records (ADR-022 through ADR-027)
```

## How it deploys

The copilot follows the same golden path as every other platform service:

- **CI**: GitHub Actions builds a linux/amd64 image, tags it with the git SHA, pushes to ECR
- **CD**: ArgoCD ApplicationSet detects `services/alert-copilot/` in `platform-golden-path` and syncs automatically
- **Helm**: Uses the shared library chart (deployment, service, PDB, external secret)
- **Secrets**: Claude API key stored in AWS Secrets Manager, synced to Kubernetes by ESO

No special deploy process. Same pipeline, same chart, same ArgoCD.

## Key design decisions

| Decision | Rationale |
|----------|-----------|
| Python + FastAPI over Go | Developer speed matters more than runtime speed for a webhook receiver |
| Pydantic validation | Malformed payloads return 422 automatically, service never crashes on bad input |
| Prometheus instant queries | Copilot needs current values, not time series — saves latency and LLM tokens |
| Claude Sonnet over Opus | Triage is structured, not open-ended — Sonnet is faster, cheaper, and sufficient |
| ESO for API keys | Centralized secret management, audit trail, auto-rotation — no secrets in Git |
| Discord for lab notifications | Free Slack stand-in, same webhook pattern — one URL change to switch to Slack |

See `docs/decisions.md` for full ADRs.

## Lab vs production

| Aspect | Lab | Production |
|--------|-----|------------|
| Notification channel | Discord webhook | Slack + PagerDuty |
| Secret management | ESO + Secrets Manager | Same, plus key rotation policies |
| Replicas | 1 | 2+ with PDB |
| AlertmanagerConfig | Single namespace-scoped CRD | Global config or per-namespace CRDs |
| Observability | Pod logs | Structured logging, SLO on copilot itself |
| Prompt tuning | Basic system prompt | Iterated with real incident data |
| Rate limiting | None | Token budget per alert, dedup for flapping alerts |

## Running locally

```bash
pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 8080
```

Test the health endpoint:
```bash
curl http://localhost:8080/healthz
```

Test the webhook with a fake Alertmanager payload:
```bash
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "status": "firing",
    "alerts": [{
      "status": "firing",
      "labels": {"alertname": "TestAlert", "namespace": "orders", "service": "orders-service", "severity": "critical"},
      "annotations": {"summary": "Test alert"},
      "startsAt": "2026-04-30T00:00:00Z",
      "endsAt": "0001-01-01T00:00:00Z",
      "fingerprint": "abc123"
    }],
    "groupLabels": {"alertname": "TestAlert"},
    "commonLabels": {"severity": "critical"}
  }'
```

Note: Prometheus enrichment and Claude API calls only work inside the cluster or with proper credentials.

## Part of the platform portfolio

This is Project 5 of 5 in a connected DevOps/Platform/SRE portfolio sprint on AWS EKS. It builds on top of:

- **Project 1 — Golden Path**: Helm library chart and ArgoCD ApplicationSet (how this service deploys)
- **Project 2 — Observability**: SLOs, burn-rate alerts, and Alertmanager config (what generates the alerts)
- **Project 3 — Progressive Delivery**: Argo Rollouts and canary analysis (deployment safety)
- **Project 4 — Spike Autoscaling**: Karpenter and KEDA (handles traffic spikes)