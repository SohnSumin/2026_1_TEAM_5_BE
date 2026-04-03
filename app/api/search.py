from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app import models, schemas
from app.api.deps import get_current_user
from uuid import UUID
from typing import List
from math import radians, cos, sin, asin, sqrt

router = APIRouter(prefix="/api/search", tags=["search"])

def get_distance(lat1, lon1, lat2, lon2):
    R = 6371000  # 지구 반지름 (미터 단위)
    dLat = radians(lat2 - lat1)
    dLon = radians(lon2 - lon1)
    a = sin(dLat / 2) * sin(dLat / 2) + cos(radians(lat1)) * \
        cos(radians(lat2)) * sin(dLon / 2) * sin(dLon / 2)
    c = 2 * asin(sqrt(a))
    return R * c
# [GET] 시니어 맞춤형 공고 검색
@router.get("/jobs", response_model=List[schemas.JobPostResponse])
def get_searched_jobs_for_senior(
    range_m: int = 15000,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "SENIOR":
        raise HTTPException(status_code=403, detail="시니어만 추천 공고를 볼 수 있습니다.")

    # 1) 시니어 정보 가져오기
    senior = db.query(models.SeniorProfile).filter(models.SeniorProfile.user_id == current_user.user_id).first()
    if not senior:
        raise HTTPException(status_code=404, detail="시니어 프로필을 찾을 수 없습니다.")
    
    # 2) 시니어의 거점들 (current_user.locations 관계가 설정되어 있다면 바로 쓸 수 있습니다)
    locations = db.query(models.SeniorLocation).filter(models.SeniorLocation.user_id == current_user.user_id).all()
    
    # 3) 전체 OPEN된 공고를 한 번에 가져오기
    jobs = db.query(models.JobPost).filter(models.JobPost.status == "OPEN").all()

    recommended = []
    for job in jobs:
        # 거리 체크: 거점 중 하나라도 범위 내에 있으면 OK
        if any(get_distance(job.latitude, job.longitude, loc.latitude, loc.longitude) <= range_m for loc in locations):
            recommended.append(job)

    return recommended


# [GET] 특정 공고에 적합한 주변 시니어 목록 추천
@router.get("/seniors/{post_id}", response_model=List[schemas.SeniorDetailResponse])
def get_searched_seniors(
    post_id: UUID,
    range_m: int = 15000,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "REQUESTER":
        raise HTTPException(status_code=403, detail="요청자만 시니어를 검색할 수 있습니다.")

    job = db.query(models.JobPost).filter(models.JobPost.post_id == post_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="공고를 찾을 수 없습니다.")
    
    # 💡 [핵심수정] joinedload를 사용하여 시니어 프로필을 가져올 때 거점 정보까지 한 번에 가져옵니다.
    # 이렇게 하면 루프 안에서 쿼리가 발생하지 않습니다.
    all_seniors = db.query(models.SeniorProfile).options(joinedload(models.SeniorProfile.user)).all()

    recommended = []
    for senior in all_seniors:
        # 시니어의 거점 리스트 (유저 모델을 통해 연결된 경우)
        user_locations = db.query(models.SeniorLocation).filter(models.SeniorLocation.user_id == senior.user_id).all()
        
        if any(get_distance(job.latitude, job.longitude, loc.latitude, loc.longitude) <= range_m for loc in user_locations):
            recommended.append(senior)

    return recommended