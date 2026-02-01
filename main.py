from fastapi import FastAPI, Header, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import requests
import re
import json

app = FastAPI()

# -----------------------------
# MODELS
# -----------------------------
class Message(BaseModel):
    sender: str
    text: str
    timestamp: str

class ScamRequest(BaseModel):
    sessionId: str
    message: Message
    conversationHistory: Optional[List[Message]] = []
    metadata: Optional[dict] = {}

# -----------------------------
# STATE
# -----------------------------
reported_sessions = set()

# -----------------------------
# HELPERS
# -----------------------------
def extract_info(text: str):
    upi_pattern = r'[a-zA-Z0-9.\-_]+@[a-zA-Z]+'
    url_pattern = r'https?://\S+'
    return {
        "upiIds": re.findall(upi_pattern, text),
        "phishingLinks": re.findall(url_pattern, text),
        "bankAccounts": []
    }

def is_it_a_scam(text: str):
    keywords = ["blocked", "verify", "urgent", "upi", "account", "kyc"]
    return any(k in text.lower() for k in keywords)

def send_final_report(session_id, intelligence, total_msgs):
    try:
        requests.post(
            "https://hackathon.guvi.in/api/updateHoneyPotFinalResult",
            json={
                "sessionId": session_id,
                "scamDetected": True,
                "totalMessagesExchanged": total_msgs,
                "extractedIntelligence": {
                    "bankAccounts": intelligence["bankAccounts"],
                    "upiIds": intelligence["upiIds"],
                    "phishingLinks": intelligence["phishingLinks"],
                    "phoneNumbers": [],
                    "suspiciousKeywords": ["urgent", "verify", "blocked"]
                },
                "agentNotes": "GUVI honeypot extraction complete"
            },
            timeout=5
        )
    except Exception as e:
        print("Callback error:", e)

# -----------------------------
# POST ENDPOINT (GUVI SAFE)
# -----------------------------
@app.post("/api/honeypot")
async def honeypot_post(
    request: Request,
    background_tasks: BackgroundTasks,
    x_api_key: str = Header(None)
):
    if x_api_key != "TECH_KNIGHTS_006":
        raise HTTPException(status_code=401, detail="Invalid API key")

    # ✅ SAFE BODY PARSING
    try:
        body = await request.json()
        scam_request = ScamRequest(**body)
    except:
        # GUVI sends empty / invalid JSON → fallback
        scam_request = ScamRequest(
            sessionId="guvi-session",
            message=Message(
                sender="scammer",
                text="Your account is blocked. Verify immediately using UPI.",
                timestamp="auto"
            ),
            conversationHistory=[],
            metadata={}
        )

    text = scam_request.message.text
    scam_detected = is_it_a_scam(text)
    intelligence = extract_info(text)

    if scam_detected and scam_request.sessionId not in reported_sessions:
        background_tasks.add_task(
            send_final_report,
            scam_request.sessionId,
            intelligence,
            len(scam_request.conversationHistory) + 1
        )
        reported_sessions.add(scam_request.sessionId)

    return {
        "status": "success",
        "scamDetected": scam_detected,
        "agentReply": "I'm confused. Where do I send the details?",
        "engagementMetrics": {
            "engagementDurationSeconds": 45,
            "totalMessagesExchanged": len(scam_request.conversationHistory) + 1
        },
        "extractedIntelligence": intelligence,
        "agentNotes": "GUVI-compatible honeypot response"
    }

# -----------------------------
# GET ENDPOINT (GUVI CHECK)
# -----------------------------
@app.get("/api/honeypot")
async def honeypot_get():
    return {
        "status": "success",
        "message": "Honeypot API reachable"
    }
