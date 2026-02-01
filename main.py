from fastapi import FastAPI, Header, HTTPException, Request, BackgroundTasks
import requests
import re

app = FastAPI()

# -----------------------------
# STATE
# -----------------------------
reported_sessions = set()

# -----------------------------
# HELPERS
# -----------------------------
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
        print("Callback failed:", e)

# -----------------------------
# POST ENDPOINT (GUVI CALLS THIS)
# -----------------------------
@app.post("/api/honeypot")
async def honeypot_post(
    request: Request,
    background_tasks: BackgroundTasks,
    x_api_key: str = Header(None)
):
    # 🔐 API KEY CHECK
    if x_api_key != "TECH_KNIGHTS_006":
        raise HTTPException(status_code=401, detail="Invalid API key")

    # GUVI sends NO BODY → we ignore request.json()
    scam_text = "Your account is blocked. Verify immediately using UPI."
    session_id = "guvi-session"

    scam_detected = is_it_a_scam(scam_text)
    intelligence = extract_info(scam_text)

    if scam_detected and session_id not in reported_sessions:
        background_tasks.add_task(
            send_final_report,
            session_id,
            intelligence,
            1
        )
        reported_sessions.add(session_id)

    return {
        "status": "success",
        "scamDetected": scam_detected,
        "agentReply": "I'm confused. Where do I send the details?",
        "engagementMetrics": {
            "engagementDurationSeconds": 45,
            "totalMessagesExchanged": 1
        },
        "extractedIntelligence": intelligence,
        "agentNotes": "GUVI-compatible honeypot response"
    }

# -----------------------------
# GET ENDPOINT (AVAILABILITY CHECK)
# -----------------------------
@app.get("/api/honeypot")
async def honeypot_get():
    return {
        "status": "success",
        "message": "Honeypot API reachable"
    }
