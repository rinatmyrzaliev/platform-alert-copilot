from pydantic import BaseModel
from datetime import datetime


class Alert(BaseModel):
    status: str
    labels: dict
    annotations: dict
    startsAt: datetime
    endsAt: datetime
    fingerprint: str


class WebhookPayload(BaseModel):
    status: str
    alerts: list[Alert]
    groupLabels: dict
    commonLabels: dict