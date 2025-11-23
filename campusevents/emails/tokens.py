from django.core.signing import TimestampSigner

_signer = TimestampSigner(salt="campusevents.ticket")

def make_email_token(payload: str) -> str:
    return _signer.sign(payload)

def read_email_token(token: str, max_age_seconds: int = 3600) -> str:
    return _signer.unsign(token, max_age=max_age_seconds)
