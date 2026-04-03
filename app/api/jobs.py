from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from geoalchemy2.elements import WKTElement
from typing import List
from app.core.database import get_db
from app import models, schemas
from uuid import UUID
from app.api.deps import get_current_user
from app.utils.ai_tags import extract_job_post_tags
from app.utils.vector_embedding import get_embedding

from app.db.seed import TAGS_DATA


router = APIRouter(prefix="/api/jobs", tags=["jobs"])

router.post("/tags/recommend")
def recommend_tags(payload: schemas.TagRecommendRequest):
    """
    사용자의 자기소개를 바탕으로 AI가 적절한 태그 5개를 추천합니다.
    """
    recommended = extract_job_post_tags(payload.content)
    return {"recommended_tags": recommended}

# [POST] 새로운 소일거리 공고 등록 (이미지 포함)
@router.post("", response_model=schemas.JobPostResponse)
def create_job(
    payload: schemas.JobPostCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "REQUESTER":
        raise HTTPException(status_code=403, detail="요청자만 공고를 등록할 수 있습니다.")

# 1. 변수 초기화 (중요: 에러 방지)
    final_main_tags = payload.main_tags[0] if payload.main_tags else None
    final_sub_tags = payload.sub_tags[0] if payload.sub_tags else None

    # 3) SeniorProfile 생성 (AI 태그 추출 포함)
    final_sub_tags = payload.sub_tags if payload.sub_tags else extract_job_post_tags(payload.content)

    # AI가 추출한 서브 태그들이 속한 메인 태그들을 추출하여 저장
    final_main_tags = []
    for sub in final_sub_tags:
        for category in TAGS_DATA:
            if sub in category["sub"]:
                final_main_tags.append(category["main"])
                break

    # 태그가 끝까지 추출되지 않았을 경우에 대한 예외 처리
    if not final_sub_tags or not final_main_tags:
        raise HTTPException(
            status_code=400, 
            detail="자기소개를 더 자세히 적어주시거나 관심 태그를 선택해주세요."
        )
    
    # 💡 제목 + 본문 결합하여 임베딩 생성
    combined_text = f"{payload.title} {payload.content}"
    job_embedding = get_embedding(combined_text)

    # 4) JobPost 생성
    new_job = models.JobPost(
        requester_id=current_user.user_id,
        title=payload.title,
        content=payload.content,
        main_tags=final_main_tags,
        sub_tags=final_sub_tags,
        job_date=payload.job_date,
        location_name=payload.location_name,
        latitude=payload.latitude,
        longitude=payload.longitude,
        start_time=payload.start_time,
        embedding=job_embedding,
        reward=payload.reward,
        status="OPEN"
        # thumbnail_url=payload.thumbnail_url
    )
    db.add(new_job)
    db.flush() # ID 확보

    # 이미지 URL 저장
    for url in payload.image_urls:
        db.add(models.JobImage(post_id=new_job.post_id, image_url=url))
    
    db.commit()
    db.refresh(new_job)
    return new_job

# [GET] 내가 작성한 공고 목록 조회
@router.get("/my", response_model=List[schemas.JobPostResponse])
def get_my_jobs(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(models.JobPost).filter(models.JobPost.requester_id == current_user.user_id).all()

# [GET] 특정 공고 상세 정보 조회
@router.get("/{post_id}", response_model=schemas.JobPostDetailResponse)
def get_job_detail(post_id: UUID, db: Session = Depends(get_db)):
    job = db.query(models.JobPost).filter(models.JobPost.post_id == post_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="공고를 찾을 수 없습니다.")
    return job

# [PATCH] 공고 내용 수정 또는 모집 상태 변경
@router.patch("/{post_id}")
def update_job(
    post_id: UUID,
    payload: schemas.JobPostUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    job = db.query(models.JobPost).filter(models.JobPost.post_id == post_id).first()
    if not job or job.requester_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="권한이 없거나 공고가 없습니다.")

    update_data = payload.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(job, key, value)
    
    if "title" in update_data or "content" in update_data:
        combined_text = f"{job.title} {job.content}"
        job.embedding = get_embedding(combined_text)

    db.commit()
    return {"message": "수정 완료"}

# [DELETE] 공고 삭제 (연관된 매칭 및 이미지 포함)
@router.delete("/{post_id}")
def delete_job(
    post_id: UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    job = db.query(models.JobPost).filter(models.JobPost.post_id == post_id).first()
    if not job or job.requester_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="권한이 없거나 공고가 없습니다.")
    
    db.delete(job)
    db.commit()
    return {"message": "삭제 완료"}