import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google import genai
from google.genai import types

app = Flask(__name__)

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

conversation_history = {}

SYSTEM_PROMPT = "You are Simran's AI learning coach. She is a fintech PM learning AI over 4 weeks. When she tells you what she studied, quiz her with exactly 10 questions one by one. Keep responses short, this is WhatsApp. After all 10 answers, give her a score out of 10 and tell her if she passed (8+) or needs to retry."

@app.route("/webhook", methods=["POST"])
def webhook():
    incoming_msg = request.values.get("Body", "").strip()
    sender = request.values.get("From", "")

    if sender not in conversation_history:
        conversation_history[sender] = []

    conversation_history[sender].append(
        types.Content(role="user", parts=[types.Part(text=incoming_msg)])
    )

    response = client.models.generate_content(
        model="gemini-1.5-flash",
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
        contents=conversation_history[sender]
    )

    reply = response.text

    conversation_history[sender].append(
        types.Content(role="model", parts=[types.Part(text=reply)])
    )

    resp = MessagingResponse()
    resp.message(reply)
    return str(resp)

@app.route("/", methods=["GET"])
def home():
    return "WhatsApp webhook is running!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
