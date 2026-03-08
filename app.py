import os
import re
import requests
from flask import Flask, request
from datetime import datetime

app = Flask(__name__)

# API Keys
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
SHEETS_URL = "https://script.google.com/macros/s/AKfycbwVSIFlrNPY8zsOurN-K90X40r7efcpG7sYTPYBlaKoc3dCMJDK6OF-rcMJfHyPNlkIFg/exec"

# Store conversation history and quiz state per user
conversation_history = {}
quiz_state = {}  # tracks question count, module and scores per user

SYSTEM_PROMPT = """You are Simran's AI learning coach. She is a fintech PM learning AI over 4 weeks.

When she tells you what she studied, quiz her with exactly 10 questions one by one.
- Ask one question at a time
- Wait for her answer before asking the next
- Keep responses short — this is Telegram
- After all 10 answers, give her a score out of 10 with format: "Score: X/10"
- Tell her if she passed (8+) or needs to retry
- Be encouraging but honest"""

def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def sync_to_sheets(module, status, score):
    try:
        requests.post(SHEETS_URL, json={
            "module": module,
            "status": status,
            "score": score,
            "date": datetime.now().strftime("%d/%m/%Y"),
            "source": "telegram"
        })
    except Exception as e:
        print(f"Sheets sync error: {e}")

def get_claude_response(user_id, user_message):
    if user_id not in conversation_history:
        conversation_history[user_id] = []

    conversation_history[user_id].append({"role": "user", "content": user_message})

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01"
        },
        json={
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 1000,
            "system": SYSTEM_PROMPT,
            "messages": conversation_history[user_id]
        }
    )

    if not response.ok:
        err = response.json()
        raise Exception(f"{response.status_code} — {err.get('error', {}).get('message', 'Unknown error')}")

    reply = response.json()["content"][0]["text"]
    conversation_history[user_id].append({"role": "assistant", "content": reply})

    return reply

def extract_score(text):
    """Extract score from Claude's response like 'Score: 7/10'"""
    match = re.search(r'[Ss]core[:\s]+(\d+)\s*/\s*10', text)
    if match:
        return int(match.group(1))
    return None

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    if "message" not in data:
        return "ok", 200

    message = data["message"]
    chat_id = message["chat"]["id"]
    user_id = str(chat_id)

    if "text" not in message:
        send_telegram_message(chat_id, "Please send a text message.")
        return "ok", 200

    user_text = message["text"].strip()

    if user_text == "/start":
        send_telegram_message(chat_id,
            "👋 *Hey Simran!*\n\nI'm your AI learning coach.\n\nTell me what you studied today and I'll quiz you on it!\n\nFor example: _'I studied how LLMs work — 3Blue1Brown Neural Networks'_")
        return "ok", 200

    if user_text == "/reset":
        conversation_history[user_id] = []
        quiz_state[user_id] = {}
        send_telegram_message(chat_id, "✅ Conversation reset. Tell me what you studied!")
        return "ok", 200

    # Save module name from first message
    if user_id not in quiz_state:
        quiz_state[user_id] = {"module": user_text, "synced": False}

    try:
        reply = get_claude_response(user_id, user_message=user_text)
        send_telegram_message(chat_id, reply)

        # Check if quiz is complete by looking for score in reply
        score = extract_score(reply)
        if score is not None and not quiz_state.get(user_id, {}).get("synced"):
            module = quiz_state.get(user_id, {}).get("module", "Unknown")
            status = "passed" if score >= 8 else "failed"
            sync_to_sheets(module, status, score)
            quiz_state[user_id]["synced"] = True

    except Exception as e:
        send_telegram_message(chat_id, f"❌ Something went wrong: {str(e)}")

    return "ok", 200

@app.route("/", methods=["GET"])
def home():
    return "Telegram bot is running!"

@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    railway_url = os.environ.get("RAILWAY_URL", "")
    webhook_url = f"{railway_url}/webhook"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook?url={webhook_url}"
    response = requests.get(url)
    return response.json()
