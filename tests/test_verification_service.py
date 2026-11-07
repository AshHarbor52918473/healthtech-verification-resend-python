from src.verification_service import VerificationRequest, resend_verification


class FakeClient:
    def __init__(self):
        self.calls = []

    def sms_resend(self, message_id):
        self.calls.append(("resend", message_id))

    def sms_events(self, message_id):
        self.calls.append(("events", message_id))
        return [{"status": "delivered"}]


def test_resend_then_report_delivery_for_the_appointment():
    client = FakeClient()
    result = resend_verification(
        VerificationRequest("apt-42", "patient-42", "msg-42"), client
    )
    assert result.appointment_id == "apt-42"
    assert result.patient_reference == "patient-42"
    assert result.state == "delivered"
    assert client.calls == [("resend", "msg-42"), ("events", "msg-42")]
