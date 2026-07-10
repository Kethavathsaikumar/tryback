from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from datetime import datetime
import os
import traceback

DATABASE_URL = os.getenv("DATABASE_URL")
print("DATABASE_URL LOADED:", DATABASE_URL[:30] + "..." if DATABASE_URL else "NONE")

# THIS WORKS WITH MYSQL
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app = FastAPI(title="HCP CRM Backend - MySQL")

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

# Auto create table on startup
Base.metadata.create_all(bind=engine)

class InteractionRequest(BaseModel):
    hcp_name: str
    interaction_text: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def analyze_notes(text: str):
    text_lower = text.lower()
    if "positive" in text_lower or "good" in text_lower or "happy" in text_lower:
        sentiment = "Positive"
    elif "negative" in text_lower or "issue" in text_lower or "complain" in text_lower:
        sentiment = "Negative"
    else:
        sentiment = "Neutral"

    summary = f"Key points: {text[:120]}..."
    next_action = "Follow up next week" if "follow" in text_lower else "Send samples" if "sample" in text_lower else "Schedule next meeting"
    return summary, sentiment, next_action

@app.get("/")
def root():
    return {"message": "Backend running with MySQL ✅"}

@app.post("/interactions")
def create_interaction(req: InteractionRequest, db: Session = Depends(get_db)):
    try:
        summary, sentiment, next_action = analyze_notes(req.interaction_text)
        new_interaction = Interaction(
            hcp_name=req.hcp_name,
            interaction_text=req.interaction_text,
            ai_summary=summary,
            sentiment=sentiment,
            next_action=next_action
        )
        db.add(new_interaction)
        db.commit()
        db.refresh(new_interaction)
        return new_interaction
    except Exception as e:
        print("ERROR:", traceback.format_exc()) # Shows in Render logs
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/interactions")
def get_interactions(db: Session = Depends(get_db)):
    return db.query(Interaction).order_by(Interaction.created_at.desc()).all()
