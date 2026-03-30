from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import engine, Base
from app.api import auth
from app import models  # 반드시 임포트해야 metadata에 모델 정보가 등록됩니다.

# 서버 시작 시 RDS에 테이블 자동 생성 (스키마 반영)
try:
    Base.metadata.create_all(bind=engine)
    print("--- [RDS] Database tables created or already exist ---")
except Exception as e:
    print(f"--- [RDS Connection Error] ---\n{e}")

app = FastAPI(title="SEENEAR API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)

@app.get("/")
def root():
    return {"message": "SEENEAR RDS Server is Live!"}