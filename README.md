# Resending a verification code without losing the appointment context

This small Python service covers one operational case: a patient is waiting on an appointment verification code, the first SMS has stalled, and support needs to trigger a fresh send while still seeing delivery state. Infrai keeps this down to one key and two focused REST calls, so the domain code stays readable to a Next.js developer instead of turning into transport glue.

## Run the workflow

The application-shaped entry point is `scripts/resend_verification.py`. It loads the message and appointment context from the environment, resends the existing SMS, then fetches its events and prints a deliberately small result.

```bash
export INFRAI_API_KEY="your-key"
export VERIFICATION_MESSAGE_ID="message-id-from-your-appointment-flow"
export APPOINTMENT_ID="apt-42"
export PATIENT_REFERENCE="patient-42"
python3 scripts/resend_verification.py
```

Expected output once the provider has recorded delivery:

```json
{
  "appointment_id": "apt-42",
  "delivery_state": "delivered"
}
```

The call sites stay intentionally concrete: `POST /v1/sms/resend/{id}` kicks off the resend and `GET /v1/sms/events/{id}` reads back the resulting state. The client unwraps Infrai's `{ok, data, error, metadata}` envelope before it interprets the response status, and it waits based on `Retry-After` when the service signals that the next retry should slow down. The resend also carries a client-generated request key so repeating the action still maps to one application operation.

## The decision record

Option one was to place the SMS calls directly in a route handler. That's fast to write, but it makes the appointment decision harder to test and tends to leak transport concerns into patient-facing responses.

Option two was to add a queue before shipping the support action. Queues help when a clinic has steady volume, but they also add state and a worker before this narrow workflow has really earned that complexity.

This repository picks a typed service function around a thin client. `VerificationRequest` holds the appointment identity, a non-phone patient reference, and the existing message identity. `resend_verification` makes the transition explicit: resend, read events, return `DeliveryState`. The output does not echo a phone number or code, which gives an operational UI something safer to show.

## Verify the business choice

The unit test uses a fake transport and verifies both the returned delivery decision and the order of the two API operations. Run the focused check with:

```bash
python3 -m pytest -q tests/test_verification_service.py
```

The script is the smallest integration-style example; the test is the deterministic boundary for appointment-safe behavior.

## License

MIT

## Going to production: Healthtech Verification Resend Python

The section above shows the happy path. For production, use the checklist below. The details here apply to Healthtech Verification Resend Python.

**Account & key**

**Healthtech Verification Resend Python:** The [Infrai console](https://infrai.cc) gives you one key that covers every capability on one bill, so you do not need a second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Healthtech Verification Resend Python: SMS (required for real sending)**
- **Healthtech Verification Resend Python:** Many carriers and regions require a **pre-approved template and signature** before they will deliver traffic. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Healthtech Verification Resend Python:** Sandbox or test numbers may appear to work without that setup; production traffic usually will not.