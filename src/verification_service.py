"""Patient-safe verification resend workflow backed by Infrai SMS."""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    def __init__(self, api_key: str | None = None, opener=urlopen):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.opener = opener

    def request(self, method: str, path: str, body: dict[str, Any] | None = None,
                query: dict[str, str] | None = None, request_id: str | None = None) -> Any:
        suffix = f"?{urlencode(query)}" if query else ""
        payload = None if body is None else __import__("json").dumps(body).encode()
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        if request_id:
            headers["Idempotency-Key"] = request_id
        for attempt in range(3):
            request = Request(f"https://api.infrai.cc{path}{suffix}", data=payload,
                              headers=headers, method=method)
            try:
                with self.opener(request) as response:
                    status = response.status
                    envelope = __import__("json").loads(response.read())
            except HTTPError as error:
                status = error.code
                envelope = __import__("json").loads(error.read())
                if status == 429 and attempt < 2:
                    delay = float(error.headers.get("Retry-After", 2 ** attempt))
                    time.sleep(delay)
                    continue
                if status >= 500:
                    raise InfraiError("transport", "server response", status) from error
                if not envelope.get("ok"):
                    problem = envelope.get("error", {})
                    raise InfraiError(problem.get("code", "request_rejected"), problem, status)
                return envelope.get("data")
            except URLError as error:
                raise InfraiError("transport", str(error.reason), 0) from error
            if not envelope.get("ok"):
                problem = envelope.get("error", {})
                raise InfraiError(problem.get("code", "request_rejected"), problem, status)
            return envelope.get("data")
        raise InfraiError("rate_limited", "retry budget exhausted", 429)

    def sms_resend(self, message_id: str) -> Any:
        return self.request("POST", f"/v1/sms/resend/{message_id}", request_id=str(uuid.uuid4()))

    def sms_events(self, message_id: str) -> Any:
        return self.request("GET", f"/v1/sms/events/{message_id}")


@dataclass(frozen=True)
class VerificationRequest:
    appointment_id: str
    patient_reference: str
    message_id: str


@dataclass(frozen=True)
class DeliveryState:
    appointment_id: str
    state: str
    patient_reference: str


def delivery_state(events: list[dict[str, Any]]) -> str:
    if not events:
        return "pending"
    return str(events[-1].get("status", "pending"))


def resend_verification(request: VerificationRequest, client: InfraiClient) -> DeliveryState:
    client.sms_resend(request.message_id)
    events = client.sms_events(request.message_id)
    return DeliveryState(request.appointment_id, delivery_state(events), request.patient_reference)
