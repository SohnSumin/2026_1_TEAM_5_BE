from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
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

# [GET] 시니어 맞춤형 공고 검색 (관심 태그 및 활동 거점 거리 기반)
@router.get("/jobs", response_model=List[schemas.JobPostResponse])
def get_searched_jobs_for_senior(
    range_m: int = 15000,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "SENIOR":
        raise HTTPException(status_code=403, detail="시니어만 추천 공고를 볼 수 있습니다.")

    # 1) 시니어 프로필 및 태그 가져오기
    senior = db.query(models.SeniorProfile).filter(models.SeniorProfile.user_id == current_user.user_id).first()
    if not senior or not senior.sub_tags:
        # 태그가 없으면 필터링이 불가능하므로 빈 리스트 반환 혹은 전체 거리 검색 (여기선 빈 리스트)
        return []
    
    # 2) [거리 필터링] 시니어의 3거점 중 하나라도 가까운지 확인
    locations = db.query(models.SeniorLocation).filter(models.SeniorLocation.user_id == current_user.user_id).all()
    recommended = []

    jobs = db.query(models.JobPost).filter(models.JobPost.status == "OPEN").all()

    for job in jobs:
        is_nearby = False
        for loc in locations:
            if get_distance(job.latitude, job.longitude, loc.latitude, loc.longitude) <= range_m:
                is_nearby = True
                break
        if is_nearby:
            recommended.append(job)

    return recommended


# [GET] 특정 공고에 적합한 주변 시니어 목록 추천 (요청자용)
@router.get("/seniors/{post_id}", response_model=List[schemas.SeniorDetailResponse])
def get_searched_seniors(
    post_id: UUID,
    range_m: int = 15000,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "REQUESTER":
        raise HTTPException(status_code=403, detail="요청자만 시니어를 검색할 수 있습니다.")

    # 1) 공고 정보 및 태그 파악
    job = db.query(models.JobPost).filter(models.JobPost.post_id == post_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="공고를 찾을 수 없습니다.")
    
    all_seniors = db.query(models.SeniorProfile).all()

    recommended = []

    # 2) [거리 필터링] 후보 시니어들의 거점 확인
    for senior in all_seniors:
        is_nearby = False
        locations = db.query(models.SeniorLocation).filter(models.SeniorLocation.user_id == senior.user_id).all()
        for loc in locations:
            dist = get_distance(job.latitude, job.longitude, loc.latitude, loc.longitude)
            if dist <= range_m:
                is_nearby = True
                break
        
        if is_nearby:
            recommended.append(senior)

    return recommended
