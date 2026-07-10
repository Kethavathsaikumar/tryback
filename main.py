from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
import os
from datetime import datetime

# 1. DATABASE SETUP - Use Render MySQL
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise Exception("DATABASE_URL not found. Add it in Render Environment Variables")

# For MySQL you need pymysql
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. FASTAPI APP + CORS
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://tryfront.onrender.com"],  # Your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. DATABASE MODEL
class Interaction(Base):
    __tablename__ = "interactions"
    
    id = Column(Integer, primary_key=True, index=True)
    notes = Column(Text)
    extracted_data = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# 4. REQUEST MODEL
class NotesRequest(BaseModel):
    notes: str

# 5. API ROUTES
@app.get("/")
def root():
    return {"message": "Backend is running"}

@app.post("/extract")
def extract_notes(req: NotesRequest):
    db = SessionLocal()
    try:
        extracted = f"Extracted from: {req.notes}"
        
        new_interaction = Interaction(
            notes=req.notes,
            extracted_data=extracted
        )
        db.add(new_interaction)
        db.commit()
        db.refresh(new_interaction)
        
        return {"status": "success", "data": extracted, "id": new_interaction.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/interactions")
def get_interactions():
    db = SessionLocal()
    try:
        interactions = db.query(Interaction).order_by(Interaction.created_at.desc()).all()
        return [{"id": i.id, "notes": i.notes, "extracted_data": i.extracted_data, "created_at": i.created_at} for i in interactions]
    finally:
        db.close()
