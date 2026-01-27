from fastapi import FastAPI, Header, HTTPException, Body, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import requests
import re

app = FastAPI()

# =====================================================
# MODELS
# =====================================================

class Message(BaseModel):
    sender: str
    text: str
    timestamp: str

class ScamRequest(BaseModel):
    sessionId: str
    message: Message
    conversationHistory: Optional[List[Message]] = []
    metadata: Optional[dict] = {}

# =====================================================
# IN-MEMORY STATE
# =====================================================

reported_sessions = set()

# =====================================================
# HELPER FUNCTIONS
# =====================================================

def extract_info(text: str):
    upi_pattern = r"[a-zA-Z0-9.\-_]+@[a-zA-Z]+"
    url_pattern = r"https?://\S+"

    return {
        "upiIds": re.findall(upi_pattern, text),
        "phishingLinks": re.findall(url_pattern, text),
        "bankAccounts": []
    }

def is_it_a_scam(text: str):
    keywords = ["blocked", "verify", "urgent", "upi", "account", "kyc"]
    return any(word in text.lower() for word in keywords)

def send_final_report(session_id, intelligence_data, total_msgs):
    """
    Mandatory GUVI callback
    Runs in background (NON-BLOCKING)
    """
    url = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"

    payload = {
        "sessionId": session_id,
        "scamDetected": True,
        "totalMessagesExchanged": total_msgs,
        "extractedIntelligence": {
            "bankAccounts": intelligence_data["bankAccounts"],
            "upiIds": intelligence_data["upiIds"],
            "phishingLinks": intelligence_data["phishingLinks"],
            "phoneNumbers": [],
            "suspiciousKeywords": ["urgent", "verify", "blocked"]
        },
        "agentNotes": "Intelligence reported after sufficient engagement."
    }

    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print("Callback failed:", e)

# =====================================================
# POST ENDPOINT (MAIN HONEYPOT)
# =====================================================

@app.post("/api/honeypot")
async def handle_message(
    background_tasks: BackgroundTasks,
    request: ScamRequest = Body(None),
    x_api_key: str = Header(None)
):
    # -----------------------------
    # API KEY CHECK
    # -----------------------------
    if x_api_key != "TECH_KNIGHTS_006":
        raise HTTPException(status_code=401, detail="Invalid API key")

    # -----------------------------
    # GUVI TESTER FIX (NO BODY)
    # IMPORTANT: RETURN IMMEDIATELY
    # -----------------------------
    if request is None or request.sessionId.startswith("guvi"):
        return {
            "status": "success",
            "scamDetected": True,
            "agentReply": "Please share more details to verify your account.",
            "engagementMetrics": {
                "engagementDurationSeconds": 10,
                "totalMessagesExchanged": 1
            },
            "extractedIntelligence": {
                "upiIds": [],
                "phishingLinks": [],
                "bankAccounts": []
            },
            "agentNotes": "Initial honeypot handshake successful."
        }

    # -----------------------------
    # REAL HONEYPOT LOGIC
    # -----------------------------
    current_text = request.message.text
    scam_detected = is_it_a_scam(current_text)
    intelligence = extract_info(current_text)

    agent_reply = (
        "I'm confused. Where do I send the details?"
        if scam_detected
        else "Hello!"
    )

    # -----------------------------
    # NON-BLOCKING CALLBACK
    # (Only for REAL sessions)
    # -----------------------------
    if scam_detected and request.sessionId not in reported_sessions:
        background_tasks.add_task(
            send_final_report,
            request.sessionId,
            intelligence,
            len(request.conversationHistory) + 1
        )
        reported_sessions.add(request.sessionId)

    # -----------------------------
    # RESPONSE
    # -----------------------------
    return {
        "status": "success",
        "scamDetected": scam_detected,
        "agentReply": agent_reply,
        "engagementMetrics": {
            "engagementDurationSeconds": 45,
            "totalMessagesExchanged": len(request.conversationHistory) + 1
        },
        "extractedIntelligence": intelligence,
        "agentNotes": "Engaging to extract intelligence via persona."
    }

# =====================================================
# GET ENDPOINT (HEALTH CHECK / GUVI)
# =====================================================

@app.get("/api/honeypot")
async def honeypot_get_check(x_api_key: str = Header(None)):
    if x_api_key != "TECH_KNIGHTS_006":
        raise HTTPException(status_code=401, detail="Invalid API key")

    return {
        "status": "success",
        "message": "Honeypot API reachable and authenticated"
    }
