from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app import models, schemas
from app.api.deps import get_current_user
from uuid import UUID
from typing import List

router = APIRouter(prefix="/api/reports", tags=["reports"])

dict_report_reason_points = {
    "RUDENESS": -3,
    "UNREASON": -3,
    "TARDINESS": -2,
    "NO_SHOW": -5,
    "LATE_PAYMENT": -3,
    "NON_PAYMENT": -5,
    "POOR_QUALITY": -3
}

# [GET] 모든 신고 내역 조회 (관리자 전용)
@router.get("/all_reports", response_model=List[schemas.UserReportResponse])
def get_all_reports(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user) # current_user 주입 필요
):
    # 실제 운영 시에는 is_admin 같은 필드를 User 모델에 두는 것이 좋습니다.
    if current_user.role != "ADMIN": 
        raise HTTPException(status_code=403, detail="관리자만 접근할 수 있습니다.")
    
    # 모델명이 UserReport이므로 정확히 지정
    return db.query(models.UserReport).all()

# [POST] 새로운 신고 생성
@router.post("", response_model=schemas.UserReportResponse)
def create_report(
    payload: schemas.UserReportCreate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    if payload.reported_user_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="자신을 신고할 수 없습니다.")
    
    # 대상 유저 존재 확인
    reported_user = db.query(models.User).filter(models.User.user_id == payload.reported_user_id).first()
    if not reported_user:
        raise HTTPException(status_code=404, detail="신고 대상 사용자를 찾을 수 없습니다.")
    
    # [검증] 리스트 내의 모든 사유가 유효한지 확인
    allowed_reasons = (
        schemas.SeniorReportReason.__members__ 
        if current_user.role == "SENIOR" 
        else schemas.RequesterReportReason.__members__
    )

    # [검증] 시니어라면 요청자를, 요청자라면 시니어를 신고할 수 있도록 사유 검증
    if current_user.role == "SENIOR":
        if reported_user.role != "REQUESTER":
            raise HTTPException(status_code=400, detail="시니어는 요청자만 신고할 수 있습니다.")
    else:
        if reported_user.role != "SENIOR":
            raise HTTPException(status_code=400, detail="요청자는 시니어만 신고할 수 있습니다.")
    
    for r in payload.reason:
        if r not in allowed_reasons:
            raise HTTPException(status_code=400, detail=f"유효하지 않은 신고 사유가 포함되어 있습니다: {r}")

    reason_list = [r.value if hasattr(r, 'value') else str(r) for r in payload.reason]

    new_report = models.UserReport(
        reporter_user_id=current_user.user_id,    # 모델 필드명에 맞춤
        reported_user_id=payload.reported_user_id, # 모델 필드명에 맞춤
        reason=reason_list,
        description=payload.description,
        status="PENDING"
    )
    db.add(new_report)
    db.commit()
    db.refresh(new_report)
    return new_report

# [DELETE] 신고 삭제 (관리자 전용)
# 엔드포인트의 report_id는 신고를 
@router.delete("/{report_id}")
def delete_report(
    report_id: UUID, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="관리자만 삭제할 수 있습니다.")

    report = db.query(models.UserReport).filter(models.UserReport.report_id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="신고를 찾을 수 없습니다.") 
    
    db.delete(report)
    db.commit()
    return {"message": "신고가 삭제되었습니다."}

@router.patch("/{report_id}/status")
def update_report_status(
    report_id: UUID, 
    status: str, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="관리자만 상태를 업데이트할 수 있습니다.")
    
    if status not in ["PENDING", "RESOLVED", "REJECTED"]:
        raise HTTPException(status_code=400, detail="유효하지 않은 상태입니다.")

    # 1. 신고 내역 조회 (먼저 가져오기)
    report = db.query(models.UserReport).filter(models.UserReport.report_id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="신고를 찾을 수 없습니다.")

    # 이미 처리된 신고인지 확인 (중복 점수 차감 방지)
    if report.status == "RESOLVED" and status == "RESOLVED":
        return report

    if status == "RESOLVED":
        # 2. 피신고자 정보 조회
        reported_user = db.query(models.User).filter(models.User.user_id == report.reported_user_id).first()
        
        if reported_user:
            # 3. 점수 계산 (dict key와 데이터 타입이 일치하는지 확인)
            total_points = sum(dict_report_reason_points.get(str(r), 0) for r in report.reason)
            
            # 4. 역할별 프로필 점수 업데이트
            if reported_user.role == "SENIOR":
                profile = db.query(models.SeniorProfile).filter(models.SeniorProfile.user_id == reported_user.user_id).first()
            else: # REQUESTER
                profile = db.query(models.RequesterProfile).filter(models.RequesterProfile.user_id == reported_user.user_id).first()

            if profile:
                profile.trust_score += total_points
                # 점수가 0점 미만으로 내려가지 않게 하려면: 
                # profile.trust_score = max(0, profile.trust_score + total_points)
                db.add(profile) # 명시적으로 세션에 추가

    # 5. 신고 상태 업데이트
    report.status = status
    db.add(report)
    
    # 6. 최종 커밋 (모든 변경사항을 한 번에 반영)
    try:
        db.commit()
        db.refresh(report)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"데이터베이스 업데이트 실패: {str(e)}")

    return report