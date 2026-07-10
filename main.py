from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
Base.metadata.create_all(bind=engine) # <-- THIS CREATES TABLE

app = FastAPI(title="HCP CRM Backend")

# THIS FIXES CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://tryfront.onrender.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Interaction(Base):
    __tablename__ = "interactions"
    id = Column(Integer, primary_key=True, index=True)
    hcp_name = Column(String(255), nullable=False)
    interaction_text = Column(Text, nullable=False)
    ai_summary = Column(Text)
    sentiment = Column(String(50))
    next_action = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)

class InteractionRequest(BaseModel):
    hcp_name: str
    interaction_text: str

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def analyze_notes(text: str):
    text_lower = text.lower()
    sentiment = "Positive" if "positive" in text_lower else "Negative" if "negative" in text_lower else "Neutral"
    summary = f"Key points: {text[:100]}..."
    next_action = "Follow up next week" if "follow" in text_lower else "Send samples" if "sample" in text_lower else "Schedule next meeting"
    return summary, sentiment, next_action

@app.get("/")
def root(): return {"message": "Backend running ✅"}

@app.post("/interactions")
def create_interaction(req: InteractionRequest, db: Session = Depends(get_db)):
    summary, sentiment, next_action = analyze_notes(req.interaction_text)
    new_interaction = Interaction(hcp_name=req.hcp_name, interaction_text=req.interaction_text, ai_summary=summary, sentiment=sentiment, next_action=next_action)
    db.add(new_interaction)
    db.commit()
    db.refresh(new_interaction)
    return new_interaction

@app.get("/interactions")
def get_interactions(db: Session = Depends(get_db)):
    return db.query(Interaction).order_by(Interaction.created_at.desc()).all()
