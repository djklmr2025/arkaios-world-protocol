"""
Chat grupal para ARKAIOS World
Mensajes entre humanos + agentes en tiempo real
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from dataclasses import asdict

DB_PATH = Path(__file__).parent / 'db' / 'chat.db'

class ChatMessage:
    def __init__(self, citizen_id: str, name: str, message: str, chat_type: str = 'chat'):
        self.id = f"{citizen_id}_{datetime.now().isoformat()}"
        self.citizen_id = citizen_id
        self.name = name
        self.message = message
        self.chat_type = chat_type  # 'chat', 'emote', 'status', 'whisper'
        self.timestamp = datetime.now().isoformat()

def init_db():
    """Initialize chat database."""
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            citizen_id TEXT NOT NULL,
            name TEXT NOT NULL,
            message TEXT NOT NULL,
            chat_type TEXT DEFAULT 'chat',
            timestamp TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_message(msg: ChatMessage) -> bool:
    """Save message to database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute('''
            INSERT INTO messages (id, citizen_id, name, message, chat_type, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (msg.id, msg.citizen_id, msg.name, msg.message, msg.chat_type, msg.timestamp))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f'Error saving message: {e}')
        return False

def get_recent_messages(limit: int = 50) -> list:
    """Get recent chat messages."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute('''
            SELECT id, citizen_id, name, message, chat_type, timestamp
            FROM messages
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))

        messages = []
        for row in reversed(cursor.fetchall()):
            messages.append({
                'id': row[0],
                'citizen_id': row[1],
                'name': row[2],
                'message': row[3],
                'chat_type': row[4],
                'timestamp': row[5]
            })
        conn.close()
        return messages
    except Exception as e:
        print(f'Error fetching messages: {e}')
        return []

# SSE handlers for real-time chat
_chat_subscribers = []

def subscribe_to_chat(response):
    """Subscribe to real-time chat updates."""
    _chat_subscribers.append(response)

def broadcast_message(msg: ChatMessage):
    """Broadcast message to all connected clients."""
    msg_json = json.dumps({
        'type': 'message',
        'data': {
            'id': msg.id,
            'citizen_id': msg.citizen_id,
            'name': msg.name,
            'message': msg.message,
            'chat_type': msg.chat_type,
            'timestamp': msg.timestamp
        }
    })

    for client in _chat_subscribers[:]:
        try:
            client.write(f'data: {msg_json}\n\n')
            client.flush()
        except:
            _chat_subscribers.remove(client)
