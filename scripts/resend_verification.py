import json
import os

from src.verification_service import InfraiClient, VerificationRequest, resend_verification


message_id = os.environ["VERIFICATION_MESSAGE_ID"]
appointment_id = os.environ.get("APPOINTMENT_ID", "appointment-demo")
patient_reference = os.environ.get("PATIENT_REFERENCE", "patient-demo")
result = resend_verification(
    VerificationRequest(appointment_id, patient_reference, message_id), InfraiClient()
)
print(json.dumps({"appointment_id": result.appointment_id, "delivery_state": result.state}, indent=2))
