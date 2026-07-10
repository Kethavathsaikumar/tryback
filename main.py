from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import sqlite3
import json
import os
import re
from dotenv import load_dotenv
from groq import Groq

# 1. LOAD ENV VARIABLES
load_dotenv()

# 2. INIT FASTAPI APP
app = FastAPI(title="AI-CRM-HCP Backend")

# 3. ADD CORS - FIXES FRONTEND CONNECTION
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_NAME = "interactions.db"

# 4. GROQ CLIENT - KEY COMES FROM.env FILE
GROQ_API_KEY = os.getenv("GROQ_API_KEY") 
if not GROQ_API_KEY:
    print("WARNING: GROQ_API_KEY not found in.env file")
client = Groq(api_key=GROQ_API_KEY)

# 5. PYDANTIC MODEL FOR INPUT
class InteractionInput(BaseModel):
    text: str

# 6. DATABASE SETUP
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hcp_name TEXT,
            topic TEXT,
            sentiment TEXT,
            next_action TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# 7. AI EXTRACTION FUNCTION - FIXED VERSION
def extract_with_ai(text: str):
    prompt = f"""
    You are a CRM assistant. Extract info from the text below.
    Return ONLY a valid JSON object with these 4 keys: hcp_name, topic, sentiment, next_action.
    Rules: sentiment must be positive, negative, or neutral.

    Text: "{text}"

    JSON:
    """
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8192",
            temperature=0.1,
            max_tokens=200
        )
        response_text = chat_completion.choices[0].message.content
        # Clean JSON if AI adds ```
        response_text = response_text.replace("```json", "").replace("```", "").strip()
        return json.loads(response_text)
        
    except Exception as e:
        print(f"AI Error: {e}")
        # SMART FALLBACK: Try to extract Dr. Name manually
        name_match = re.search(r'Dr\.\s*([A-Za-z]+)', text)
        hcp_name = f"Dr. {name_match.group(1)}" if name_match else "Unknown"
        
        return {
            "hcp_name": hcp_name, 
            "topic": text[:50], 
            "sentiment": "neutral", 
            "next_action": "Follow up"
        }

# 8. API ENDPOINTS
@app.get("/")
def read_root():
    return {"status": "AI-CRM-HCP Backend is running ✅"}

@app.post("/interactions")
def create_interaction(input_data: InteractionInput):
    # Split by number if user pastes multiple notes
    notes = [note.strip() for note in input_data.text.split('\n') if note.strip()]
    results = []
    
    for note in notes:
        extracted_data = extract_with_ai(note)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO interactions (hcp_name, topic, sentiment, next_action, timestamp)
            VALUES (?,?,?,?,?)
        ''', (
            extracted_data.get("hcp_name"),
            extracted_data.get("topic"),
            extracted_data.get("sentiment"),
            extracted_data.get("next_action"),
            timestamp
        ))
        conn.commit()
        conn.close()
        results.append(extracted_data)
    
    return {"message": f"{len(results)} Interactions saved", "data": results}

@app.get("/interactions")
def get_interactions():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM interactions ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]