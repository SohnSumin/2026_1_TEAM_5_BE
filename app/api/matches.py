from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app import models, schemas
from app.api.deps import get_current_user
from uuid import UUID
from typing import List
from math import radians, cos, sin, asin, sqrt

router = APIRouter(prefix="/api/matches", tags=["matches"])

def get_distance(lat1, lon1, lat2, lon2):
    R = 6371000  # 지구 반지름 (미터 단위)
    dLat = radians(lat2 - lat1)
    dLon = radians(lon2 - lon1)
    a = sin(dLat / 2) * sin(dLat / 2) + cos(radians(lat1)) * \
        cos(radians(lat2)) * sin(dLon / 2) * sin(dLon / 2)
    c = 2 * asin(sqrt(a))
    return R * c

# [POST] 시니어가 특정 공고에 지원하기
@router.post("/apply", response_model=schemas.MatchResponse)
def apply_job(
    payload: schemas.MatchApplyRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "SENIOR":
        raise HTTPException(status_code=403, detail="시니어만 공고에 지원할 수 있습니다.")

    # 공고 존재 확인
    job = db.query(models.JobPost).filter(models.JobPost.post_id == payload.post_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="존재하지 않는 공고입니다.")

    # 이미 지원했는지 확인
    existing = db.query(models.Matching).filter(
        models.Matching.post_id == payload.post_id,
        models.Matching.senior_id == current_user.user_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="이미 지원(또는 제안)된 공고입니다.")

    # 1) 매칭 생성
    new_match = models.Matching(
        post_id=payload.post_id,
        senior_id=current_user.user_id,
        proposed_by="SENIOR",
        status="WAITING"
    )
    db.add(new_match)
    db.flush()

    # 2) 요청자에게 알림 생성
    new_noti = models.Notification(
        user_id=job.requester_id,
        related_id=new_match.match_id,
        type="PROPOSAL",
        content=f"'{job.title}' 공고에 새로운 지원자가 있습니다!"
    )
    db.add(new_noti)
    
    db.commit()
    db.refresh(new_match)
    return new_match

# [GET] 시니어 맞춤형 공고 추천 (관심 태그 및 활동 거점 거리 기반)
@router.get("/recommend-jobs", response_model=List[schemas.JobPostResponse])
def get_recommended_jobs_for_senior(
    range_m: int = 4000,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "SENIOR":
        raise HTTPException(status_code=403, detail="시니어만 추천 공고를 볼 수 있습니다.")

    # 1) 시니어 프로필 및 태그 가져오기
    senior = db.query(models.SeniorProfile).filter(models.SeniorProfile.user_id == current_user.user_id).first()
    if not senior or not senior.tags:
        # 태그가 없으면 필터링이 불가능하므로 빈 리스트 반환 혹은 전체 거리 검색 (여기선 빈 리스트)
        return []

    # 2) [태그 필터링] 공고의 태그가 시니어의 관심 태그 목록에 포함된 것만 먼저 필터링
    # DB 수준에서 .in_()을 사용하여 성능 최적화
    tagged_jobs = db.query(models.JobPost).filter(
        models.JobPost.tag.in_(senior.tags),
        models.JobPost.status == "RECRUITING"
    ).all()

    # 3) [거리 필터링] 시니어의 3거점 중 하나라도 가까운지 확인
    locations = db.query(models.SeniorLocation).filter(models.SeniorLocation.user_id == current_user.user_id).all()
    recommended = []

    for job in tagged_jobs:
        is_nearby = False
        for loc in locations:
            if get_distance(job.latitude, job.longitude, loc.latitude, loc.longitude) <= range_m:
                is_nearby = True
                break
        if is_nearby:
            recommended.append(job)

    return recommended

# [POST] 요청자가 특정 시니어에게 업무 직접 제안하기
@router.post("/propose", response_model=schemas.MatchResponse)
def propose_job(
    payload: schemas.MatchProposeRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "REQUESTER":
        raise HTTPException(status_code=403, detail="요청자만 제안할 수 있습니다.")

    job = db.query(models.JobPost).filter(models.JobPost.post_id == payload.post_id).first()
    if not job or job.requester_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="본인의 공고에만 제안할 수 있습니다.")

    # 1) 매칭 생성
    new_match = models.Matching(
        post_id=payload.post_id,
        senior_id=payload.senior_id,
        proposed_by="REQ",
        status="WAITING"
    )
    db.add(new_match)
    db.flush()

    # 2) 시니어에게 알림 생성
    new_noti = models.Notification(
        user_id=payload.senior_id,
        related_id=new_match.match_id,
        type="JOB",
        content=f"새로운 업무 제안이 도착했습니다: '{job.title}'"
    )
    db.add(new_noti)
    
    db.commit()
    db.refresh(new_match)
    return new_match

# [PATCH] 매칭 요청 수락 또는 거절 처리
@router.patch("/{match_id}/status")
def update_match_status(
    match_id: UUID,
    payload: schemas.MatchStatusUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    match = db.query(models.Matching).filter(models.Matching.match_id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="매칭 정보를 찾을 수 없습니다.")

    job = db.query(models.JobPost).filter(models.JobPost.post_id == match.post_id).first()

    if payload.status == "ACCEPTED":
        match.status = "ACCEPTED"
        job.status = "MATCHED" # 공고 상태 변경
        
        # [추가] 수락 시 해당 공고(post_id)와 관련된 모든 '대기중' 알림 삭제 (정리 로직)
        # 이 매칭뿐만 아니라 다른 지원자들에 대한 알림도 더 이상 필요 없으므로 정리합니다.
        db.query(models.Notification).filter(
            models.Notification.related_id == match_id
        ).delete()
        
        # 상대방에게 수락 알림 생성
        target_user_id = job.requester_id if current_user.role == "SENIOR" else match.senior_id
        db.add(models.Notification(
            user_id=target_user_id,
            related_id=match.match_id,
            type="ACCEPT",
            content=f"'{job.title}' 제안이 수락되었습니다! 채팅을 시작해보세요."
        ))

    elif payload.status == "REJECTED":
        match.status = "REJECTED"
        # 거절 시 해당 매칭 알림만 삭제
        db.query(models.Notification).filter(models.Notification.related_id == match_id).delete()

    db.commit()
    return {"message": f"매칭 상태가 {payload.status}로 변경되었습니다."}

# [GET] 현재 진행 중인(ACCEPTED) 매칭 목록 조회
# 시니어와 요청자 모두 본인이 포함된 'ACCEPTED' 상태의 매칭을 확인합니다.
@router.get("/active", response_model=List[schemas.MatchResponse])
def get_active_matches(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.Matching).filter(models.Matching.status == "ACCEPTED")
    
    if current_user.role == "SENIOR":
        query = query.filter(models.Matching.senior_id == current_user.user_id)
    else:
        # 요청자의 경우 본인이 쓴 공고와 연결된 매칭만 필터링
        query = query.join(models.JobPost).filter(models.JobPost.requester_id == current_user.user_id)
        
    return query.all()


# [POST] 완료된 업무의 종료 처리 (매칭 및 공고 상태 업데이트)
@router.post("/{match_id}/complete")
def complete_job(
    match_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    match = db.query(models.Matching).filter(models.Matching.match_id == match_id).first()
    if not match or match.status != "ACCEPTED":
        raise HTTPException(status_code=400, detail="종료할 수 있는 활성화된 매칭이 아닙니다.")

    job = db.query(models.JobPost).filter(models.JobPost.post_id == match.post_id).first()
    
    # 종료 권한 체크 (보통 요청자가 종료를 누르거나, 둘 다 가능하게 설정)
    match.status = "DONE"
    job.status = "DONE"
    
    # 종료 알림 생성 (시니어에게 수고했다는 알림)
    db.add(models.Notification(
        user_id=match.senior_id,
        related_id=match.match_id,
        type="DONE",
        content=f"'{job.title}' 업무가 완료 처리되었습니다. 수고하셨습니다!"
    ))
    
    db.commit()
    return {"message": "소일거리가 성공적으로 종료되었습니다."}

# [GET] 특정 공고에 적합한 주변 시니어 목록 추천 (요청자용)
@router.get("/recommend-seniors/{post_id}", response_model=List[schemas.SeniorDetailResponse])
def get_recommended_seniors(
    post_id: UUID,
    range_m: int = 4000,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "REQUESTER":
        raise HTTPException(status_code=403, detail="요청자만 시니어를 검색할 수 있습니다.")

    # 1) 공고 정보 및 태그 파악
    job = db.query(models.JobPost).filter(models.JobPost.post_id == post_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="공고를 찾을 수 없습니다.")

    # 2) [태그 필터링] 시니어의 tags(JSON/List) 필드에 공고의 태그가 포함된 시니어만 필터링
    # PostgreSQL의 JSONB를 사용한다면 contains를 쓰지만, 여기서는 일반 필터링 예시입니다.
    # senior.tags는 List[str] 형태라고 가정합니다.
    all_seniors = db.query(models.SeniorProfile).all()
    
    # 1차 필터링: 태그가 일치하는 시니어만 후보군으로 선정
    tagged_seniors = [s for s in all_seniors if s.tags and (job.category_tag in s.tags)]
    
    recommended = []

    # 3) [거리 필터링] 후보 시니어들의 거점 확인
    for senior in tagged_seniors:
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

# [GET] 내 알림 내역 조회 (최신순)
@router.get("/notifications", response_model=List[schemas.NotificationResponse])
def get_notifications(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # .all()을 호출하면 리스트가 반환되므로 위 response_model도 List여야 합니다.
    return db.query(models.Notification).filter(
        models.Notification.user_id == current_user.user_id
    ).order_by(models.Notification.created_at.desc()).all()