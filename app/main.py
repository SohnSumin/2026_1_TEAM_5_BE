from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.core.database import engine, Base
from app.api import auth, jobs, locations, matches, report
from app.db.seed import seed_categories
from app.core.database import SessionLocal
from app import models  # 반드시 임포트해야 metadata에 모델 정보가 등록됩니다.

# 서버 시작 시 RDS에 테이블 자동 생성 (스키마 반영)


app = FastAPI(title="SEENEAR API", version="1.0.0")

try:
    with engine.connect() as conn:
        conn.execute((text("CREATE EXTENSION IF NOT EXISTS postgis;")))
        conn.commit()
        
    Base.metadata.create_all(bind=engine)
    print("--- Database tables created successfully! ---")

    db = SessionLocal()
    try:
        seed_categories(db)
    finally:
        db.close()

except Exception as e:
    print(f"--- Database initialization error: {e} ---")

    
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(locations.router)
app.include_router(matches.router)
app.include_router(report.router)

@app.get("/")
def root():
    return {"message": "SEENEAR RDS Server is Live!"}

