import torch
from sentence_transformers import SentenceTransformer
from huggingface_hub import login
from sqlalchemy.orm import Session
from app import models
import os


login_token = os.getenv('HUGGINGFACE_TOKEN')
login(token=login_token)

# 1. 모델 로드 (384차원 출력을 가지는 한국어 최적화 모델)
# 서버 시작 시 한 번만 로드되도록 모듈 레벨에서 선언합니다.
MODEL_NAME = 'jhgan/ko-sbert-sts'
model = SentenceTransformer(MODEL_NAME)

def get_embedding(text: str) -> list[float]:
    """
    텍스트를 입력받아 384차원의 벡터 리스트를 반환합니다.
    """
    if not text:
        # 빈 텍스트일 경우 0으로 채워진 벡터 반환 (에러 방지)
        return [0.0] * 384
    
    # 문장 임베딩 생성
    embedding = model.encode(text)
    # numpy array를 list로 변환하여 SQLAlchemy(pgvector)가 인식 가능하게 함
    return embedding.tolist()

# --- 유사도 검색 유틸리티 (세모톤 추천 로직용) ---

def find_matching_jobs_for_senior(db: Session, senior_embedding: list, limit: int = 5):
    """
    시니어의 벡터와 가장 유사한(코사인 거리 기준) 공고를 찾아 반환합니다.
    """
    if not senior_embedding:
        return []
        
    return db.query(models.JobPost).order_by(
        models.JobPost.embedding.cosine_distance(senior_embedding)
    ).limit(limit).all()