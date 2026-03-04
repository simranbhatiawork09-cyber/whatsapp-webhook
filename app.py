import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import anthropic

app = Flask(__name__)
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

conversation_history = {}

SYSTEM_PROMPT = "You are Simran's AI learning coach. She is a fintech PM learning AI over 4 weeks. When she tells you what she studied, quiz her with exactly 10 questions one by one. Keep responses short, this is WhatsApp. After all 10 answers, give her a score out of 10 and tell her if she passed (8+) or needs to retry."

@app.route("/webhook", methods=["POST"])
def webhook():
    incoming_msg = request.values.get("Body", "").strip()
    sender = request.values.get("From", "")
    
    if sender not in conversation_history:
        conversation_history[sender] = []
    
    conversation_history[sender].append({
        "role": "user",
        "content": incoming_msg
    })
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=conversation_history[sender]
    )
    
    reply = response.content[0].text
    
    conversation_history[sender].append({
        "role": "assistant",
        "content": reply
    })
    
    resp = MessagingResponse()
    resp.message(reply)
    return str(resp)

@app.route("/", methods=["GET"])
def home():
    return "WhatsApp webhook is running!"

if __name__ == "__main__":
    app.run(debug=True)
