from fastapi import APIRouter, Depends, HTTPException, status
from typing import Union
from sqlalchemy.orm import Session
from geoalchemy2.elements import WKTElement
from app.core.database import get_db
from app import models, schemas
from app.api.deps import get_current_user 
from jose import jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv()

router = APIRouter(prefix="/api/locations", tags=["locations"])

# [GET] 현재 로그인한 시니어의 등록된 모든 활동 거점 조회
@router.get("/my", response_model=schemas.LocationListResponse)
def get_my_locations(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    locations = db.query(models.SeniorLocation).filter(models.SeniorLocation.user_id == current_user.user_id).all()
    return {"locations": locations}

# [PUT] 활동 거점 일괄 업데이트 (기존 거점 삭제 후 덮어쓰기)
@router.put("/my", response_model=schemas.LocationListResponse)
def update_my_locations(
    payload: schemas.LocationUpdateList,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. 개수 검증 (1~3개)
    if not (1 <= len(payload.locations) <= 3):
        raise HTTPException(status_code=400, detail="거점은 최소 1개, 최대 3개까지 등록 가능합니다.")

    # 2. 기존 거점 삭제 (전체 덮어쓰기 방식)
    db.query(models.SeniorLocation).filter(
        models.SeniorLocation.user_id == current_user.user_id
    ).delete()

    # 3. 새로운 데이터 삽입 (Geography 타입으로 변환)
    new_locations = []
    for loc in payload.locations:
        # WKT (Well-Known Text) 형식 생성: POINT(경도 위도) - 순서 주의!
        point_wkt = f"POINT({loc.longitude} {loc.latitude})"
        
        db_location = models.SeniorLocation(
            user_id=current_user.user_id,
            location_name=loc.location_name,
            latitude=loc.latitude,
            longitude=loc.longitude,
            is_primary=loc.is_primary,
            coords=WKTElement(point_wkt, srid=4326) # DB의 coords 컬럼에 저장
        )
        db.add(db_location)
        new_locations.append(db_location)

    db.commit()

    # 4. 응답 시에는 다시 lat, lng 숫자로 변환해서 반환해야 함 (조회 로직 필요)
    return get_my_locations(current_user, db)

# [DELETE] 특정 활동 거점 삭제 및 대표 거점 자동 승격
@router.delete("/my/{location_id}")
def delete_my_location(
    location_id: int,  # UUID라면 UUID로, int라면 int로 타입을 맞춰주세요!
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    # 1. 삭제할 거점 조회
    loc = db.query(models.SeniorLocation).filter(
        models.SeniorLocation.location_id == location_id,
        models.SeniorLocation.user_id == current_user.user_id
    ).first()
    
    if not loc:
        raise HTTPException(status_code=404, detail="거점을 찾을 수 없습니다.")
    
    # 2. 최소 개수 검증 (1개는 남겨야 함)
    remaining_count = db.query(models.SeniorLocation).filter(
        models.SeniorLocation.user_id == current_user.user_id
    ).count()
    
    if remaining_count <= 1:
        raise HTTPException(status_code=400, detail="최소 1개의 활동 거점은 유지해야 합니다.")

    # 3. 삭제 처리
    was_primary = loc.is_primary
    db.delete(loc)
    db.flush() # 삭제 반영

    # 4. [선택] 만약 대표 거점을 삭제했다면, 남은 거점 중 하나를 대표로 자동 승격
    if was_primary:
        next_loc = db.query(models.SeniorLocation).filter(
            models.SeniorLocation.user_id == current_user.user_id
        ).first()
        if next_loc:
            next_loc.is_primary = True

    db.commit()
    return {"detail": "거점이 삭제되었습니다."}
