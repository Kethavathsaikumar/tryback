from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from datetime import datetime
import os

# 1. DATABASE SETUP
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. DB MODEL
class Interaction(Base):
    __tablename__ = "interactions"
    
    id = Column(Integer, primary_key=True, index=True)
    hcp_name = Column(String(255), nullable=False)
    interaction_text = Column(Text, nullable=False)
    ai_summary = Column(Text)
    sentiment = Column(String(50))
    next_action = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)

# Create tables
Base.metadata.create_all(bind=engine)

# 3. FASTAPI APP
app = FastAPI(title="HCP CRM Backend")

# 4. CORS - Allow frontend to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Later change to: ["https://tryfront.onrender.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 5. REQUEST MODEL
class InteractionRequest(BaseModel):
    hcp_name: str
    interaction_text: str

# 6. DB DEPENDENCY
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 7. SIMPLE AI LOGIC - Replace with Gemini API later
def analyze_notes(text: str):
    text_lower = text.lower()
    
    # Sentiment
    if "positive" in text_lower or "good" in text_lower:
        sentiment = "Positive"
    elif "negative" in text_lower or "issue" in text_lower:
        sentiment = "Negative"
    else:
        sentiment = "Neutral"
    
    # Summary
    summary = f"Key points: {text[:120]}..."
    
    # Next Action
    if "follow up" in text_lower or "next week" in text_lower:
        next_action = "Follow up next week"
    elif "sample" in text_lower:
        next_action = "Send product samples"
    else:
        next_action = "Schedule next meeting"
        
    return summary, sentiment, next_action

# 8. API ROUTES
@app.get("/")
def root():
    return {"message": "HCP CRM Backend is running ✅"}

@app.post("/interactions")
def create_interaction(req: InteractionRequest, db: Session = Depends(get_db)):
    # Run AI analysis
    summary, sentiment, next_action = analyze_notes(req.interaction_text)
    
    # Save to DB
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

@app.get("/interactions")
def get_interactions(db: Session = Depends(get_db)):
    # Get all interactions, newest first
    interactions = db.query(Interaction).order_by(Interaction.created_at.desc()).all()
    return interactions
