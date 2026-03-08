import os
import requests
from flask import Flask, request
from google import genai
from google.genai import types

app = Flask(__name__)

# API Keys
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Gemini client
client = genai.Client(api_key=GEMINI_API_KEY)

# Store conversation history per user
conversation_history = {}

SYSTEM_PROMPT = """You are Simran's AI learning coach. She is a fintech PM learning AI over 4 weeks.

When she tells you what she studied, quiz her with exactly 10 questions one by one.
- Ask one question at a time
- Wait for her answer before asking the next
- Keep responses short — this is Telegram
- After all 10 answers, give her a score out of 10
- Tell her if she passed (8+) or needs to retry
- Be encouraging but honest"""

def send_telegram_message(chat_id, text):
    """Send a message back to the user on Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    requests.post(url, json=payload)

def get_gemini_response(user_id, user_message):
    """Get response from Gemini API"""
    if user_id not in conversation_history:
        conversation_history[user_id] = []

    conversation_history[user_id].append(
        types.Content(role="user", parts=[types.Part(text=user_message)])
    )

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
        contents=conversation_history[user_id]
    )

    reply = response.text

    conversation_history[user_id].append(
        types.Content(role="model", parts=[types.Part(text=reply)])
    )

    return reply

@app.route("/webhook", methods=["POST"])
def webhook():
    """Receive messages from Telegram"""
    data = request.json

    # Extract message details
    if "message" not in data:
        return "ok", 200

    message = data["message"]
    chat_id = message["chat"]["id"]
    user_id = str(chat_id)

    # Handle text messages only
    if "text" not in message:
        send_telegram_message(chat_id, "Please send a text message.")
        return "ok", 200

    user_text = message["text"].strip()

    # Handle /start command
    if user_text == "/start":
        send_telegram_message(chat_id, 
            "👋 *Hey Simran!*\n\nI'm your AI learning coach.\n\nTell me what you studied today and I'll quiz you on it!\n\nFor example: _'I studied how LLMs work — 3Blue1Brown Neural Networks'_")
        return "ok", 200

    # Handle /reset command to clear conversation
    if user_text == "/reset":
        conversation_history[user_id] = []
        send_telegram_message(chat_id, "✅ Conversation reset. Tell me what you studied!")
        return "ok", 200

    # Get AI response
    try:
        reply = get_gemini_response(user_id, user_text)
        send_telegram_message(chat_id, reply)
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg:
            send_telegram_message(chat_id, "⚠️ Quiz service is busy. Please try again in a few minutes.")
        else:
            send_telegram_message(chat_id, f"❌ Something went wrong: {error_msg}")

    return "ok", 200

@app.route("/", methods=["GET"])
def home():
    return "Telegram bot is running!"

@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    """Call this once to register webhook with Telegram"""
    railway_url = os.environ.get("RAILWAY_URL", "")
    webhook_url = f"{railway_url}/webhook"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook?url={webhook_url}"
    response = requests.get(url)
    return response.json()
