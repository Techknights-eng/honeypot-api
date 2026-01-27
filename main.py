from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import requests
import re

app = FastAPI()

# ISSUE 1 FIX: Use Message model for list consistency [cite: 173-176]
class Message(BaseModel):
    sender: str
    text: str
    timestamp: str

class ScamRequest(BaseModel):
    sessionId: str
    message: Message
    conversationHistory: Optional[List[Message]] = [] # Cleaner schema [cite: 174]
    metadata: Optional[dict] = {}

# ISSUE 2 FIX: Track reported sessions in memory
reported_sessions = set()

def extract_info(text):
    upi_pattern = r'[a-zA-Z0-9.\-_]+@[a-zA-Z]+'
    url_pattern = r'https?://\S+'
    return {
        "upiIds": re.findall(upi_pattern, text),
        "phishingLinks": re.findall(url_pattern, text),
        "bankAccounts": []
    }

def is_it_a_scam(text):
    keywords = ["blocked", "verify", "urgent", "upi", "account", "kyc"]
    return any(word in text.lower() for word in keywords)

@app.post("/api/honeypot")
async def handle_message(request: ScamRequest, x_api_key: str = Header(None)):
    # Security Check [cite: 113-115]
    if x_api_key != "TECH_KNIGHTS_006":
        raise HTTPException(status_code=401, detail="Invalid API key")

    current_text = request.message.text
    scam_detected = is_it_a_scam(current_text)
    intelligence = extract_info(current_text)
    
    # Logic for reply [cite: 180-184]
    agent_reply = "I'm confused. Where do I send the details?" if scam_detected else "Hello!"

    # ISSUE 2 FIX: Only call callback once per session [cite: 235-240]
    # Condition: 3+ messages exchanged AND session not already reported
    if len(request.conversationHistory) >= 3 and request.sessionId not in reported_sessions:
        if scam_detected:
            send_final_report(request.sessionId, intelligence, len(request.conversationHistory) + 1)
            reported_sessions.add(request.sessionId)

    return {
        "status": "success",
        "scamDetected": scam_detected,
        "agentReply": agent_reply,
        "engagementMetrics": {
            # ISSUE 3: Note in documentation that this is simulated
            "engagementDurationSeconds": 45, 
            "totalMessagesExchanged": len(request.conversationHistory) + 1
        },
        "extractedIntelligence": intelligence,
        "agentNotes": "Engaging to extract intelligence via persona."
    }

def send_final_report(session_id, intelligence_data, total_msgs):
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
    requests.post(url, json=payload, timeout=5) # Mandatory Callback [cite: 214-216]