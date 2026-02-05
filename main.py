from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Union
import re

app = FastAPI()

# =========================
# CONFIG
# =========================
API_KEY = "TECH_KNIGHTS_006"

# =========================
# DATA MODELS
# =========================
class Message(BaseModel):
    sender: str
    text: str
    timestamp: Union[int, str]  # evaluator sends number

class ScamRequest(BaseModel):
    sessionId: str
    message: Message
    conversationHistory: Optional[List[Message]] = []
    metadata: Optional[dict] = {}

# =========================
# LOGIC
# =========================
def is_scam(text: str) -> bool:
    keywords = ["blocked", "verify", "urgent", "upi", "account", "kyc"]
    text = text.lower()
    return any(word in text for word in keywords)

def agent_reply(is_scam_detected: bool) -> str:
    if is_scam_detected:
        return "Why is my account being suspended?"
    return "Hello, how can I help you?"

# =========================
# API ENDPOINT
# =========================
@app.post("/api/honeypot")
async def honeypot(
    request: ScamRequest,
    x_api_key: str = Header(None)
):
    # API key validation
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Scam detection
    scam_detected = is_scam(request.message.text)

    # Agent response (THIS IS WHAT EVALUATOR EXPECTS)
    reply_text = agent_reply(scam_detected)

    # ✅ EXACT RESPONSE FORMAT REQUIRED BY EVALUATOR
    return {
        "status": "success",
        "reply": reply_text
    }
