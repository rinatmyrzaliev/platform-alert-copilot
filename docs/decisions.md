# Architecture Decision Records — Alert-Copilot

Each ADR captures a design decision made during the Alert Copilot
project. Decisions are numbered and include context, rationale, and
consequences.

---

## ADR-022: Python + FastAPI for alert copilot

**Context:** We needed to establish system for the service copilot

**Decision:** I chose Python with FastAPI for the alert copilot service. Python was picked because most observability libraries have strong Python support. FastAPI was picked over Flask because it gives us automatic request validation with Pydantic models, built in async support for non-blocking Prometheus queries, and auto-generated API docs for free. The trade-off is slightly slower performance than Go, but for webhook receiver that processes alerts, speed is not the bottleneck - developer speed and simplicity matter more.

---

## ADR-023: ESO for API key management

**Context:** We needed to safely store secrets and API keys in centralized place 

**Decision:** I used Secrets Manager + ESO over kubectl secrets. Manually creating K8s secrets breaks GitOps because secret values live outside Git, someone must run kubectl commands by hand, and secret rotation becomes manual, error-prone tasks. With ESO, we define and ExternalSecret YAML in Git, and ESO automatically syncs secrets from AWS Secrets Manager into K8s secrets - keeping everything declarative, auditable, and auto-rotated. The trade-off is extra setup (IRSA, ClusterSecretStore, ESO operator), but once done, adding a new secret is just a values file change - no manual steps, no plaintext secrets in the repo.

---

## ADR-024: Claude Sonnet over Opus for triage

**Context:** We needed to choose model of Claude that will handle requests of our Copilot

**Decision:** We chose Claude Sonnet over Opus for the alert copilot's triage calls. Alert triage is a speed-critical task — when a pager fires at 3am, the on-call needs a dossier in seconds, not a PhD thesis, and Sonnet's lower latency wins here. Sonnet is also much cheaper per token, which matters a lot when we have a $50/month spend cap and 30+ services that can fire alerts. Opus would be overkill — our task is structured (summarize alert context and suggest next steps), not open-ended reasoning, so Sonnet handles it well and we stay within budget.

---

## ADR-025: AlertmanagerConfig namespace scoping

**Context:** We created an AlertmanagerConfig in the monitoring namespace to route alerts to the copilot. Alerts with namespace=orders were not delivered.

**Decision:** The prometheus-operator automatically injects a namespace matcher into AlertmanagerConfig routes, limiting them to alerts where namespace matches the CRD's own namespace. For the lab, we changed the test alert's namespace label. In production, options are: use the global alertmanager.yaml for cross-namespace routing, deploy one AlertmanagerConfig per namespace, or use a dedicated namespace for alert routing.

---

## ADR-026: Prometheus instant queries for enrichment

**Context:** We needed to specify in Copilot's config how much data we need to query from Prometheus

**Decision:** We use Prometheus instant queries (/api/v1/query) instead of range queries (/api/v1/query_range) when the copilot enriches an alert with extra metrics. The copilot needs a single current value — like "what is the error rate right now?" — not a full time series with hundreds of data points, so instant queries return exactly what we need. Range queries return larger JSON payloads, take longer to execute, and would waste LLM tokens feeding a time series into a prompt that only needs one number. The trade-off is we lose the "trend" view, but the alert payload already tells us something is wrong — the copilot just needs the current snapshot to build its dossier fast.

---

## ADR-027: Discord as notification channel 

**Context:** We needed to test exteranal app if we can receive the data to it

**Decision:** We use Discord webhooks for alert notifications in the lab instead of Slack, because Discord is free with no message limits, while Slack's free tier caps history and integrations. Discord works well as a Slack stand-in because both use the same pattern — a simple HTTP POST with a JSON body to a webhook URL — so switching later means changing one URL and adjusting the payload shape, not rewriting the notification logic. In production, we would swap to Slack webhooks (where the team already lives) and add PagerDuty API integration for on-call routing and escalation. The code is designed for this — the notification layer is behind an interface, so adding a new channel is one new class, not a refactor.