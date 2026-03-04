import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import google.generativeai as genai

app = Flask(__name__)

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

conversation_history = {}

SYSTEM_PROMPT = "You are Simran's AI learning coach. She is a fintech PM learning AI over 4 weeks. When she tells you what she studied, quiz her with exactly 10 questions one by one. Keep responses short, this is WhatsApp. After all 10 answers, give her a score out of 10 and tell her if she passed (8+) or needs to retry."

@app.route("/webhook", methods=["POST"])
def webhook():
    incoming_msg = request.values.get("Body", "").strip()
    sender = request.values.get("From", "")

    if sender not in conversation_history:
        conversation_history[sender] = model.start_chat(history=[])

    chat = conversation_history[sender]

    full_msg = SYSTEM_PROMPT + "\n\nUser: " + incoming_msg if len(chat.history) == 0 else incoming_msg

    response = chat.send_message(full_msg)
    reply = response.text

    resp = MessagingResponse()
    resp.message(reply)
    return str(resp)

@app.route("/", methods=["GET"])
def home():
    return "WhatsApp webhook is running!"

if __name__ == "__main__":
    app.run(debug=True)
