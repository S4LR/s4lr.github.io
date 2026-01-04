# server.py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from fastapi.middleware.cors import CORSMiddleware

# In-memory message storage (demo)
messages: List[dict] = []

app = FastAPI()

# Allow cross-origin requests (for testing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Message model
class Message(BaseModel):
    sender: str
    recipient: str
    encrypted: str

@app.post("/send_message")
def send_message(msg: Message):
    messages.append(msg.dict())
    return {"status": "ok"}

@app.get("/get_messages/{recipient}")
def get_messages(recipient: str):
    user_msgs = [m for m in messages if m["recipient"] == recipient]
    # Remove after retrieval (optional)
    for m in user_msgs:
        messages.remove(m)
    return {"messages": user_msgs}
