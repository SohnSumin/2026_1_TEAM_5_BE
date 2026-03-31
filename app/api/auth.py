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

router = APIRouter(prefix="/api/auth", tags=["auth"])

# JWT 설정 (실제 운영 환경에서는 환경 변수 .env 사용 권장)
SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES'))

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# [POST] 휴대폰 번호 기반 인증번호 발송 요청
@router.post("/otp/request")
def request_otp(payload: schemas.OTPRequest):
    # 실제 환경에서는 SMS 발송 로직이 들어가야 합니다.
    # 지금은 테스트용으로 고정된 번호를 내려줍니다.
    return {
        "message": f"{payload.phone_number}로 인증번호가 발송되었습니다.",
        "debug_otp": "123456"  # 개발 단계용 테스트 번호
    }

# [POST] OTP 번호 검증 및 로그인 처리 (JWT 토큰 발행)
@router.post("/login", response_model=schemas.Token)
def login(payload: schemas.OTPVerify, db: Session = Depends(get_db)):
    # 1) OTP 번호 검증 (테스트용 123456)
    if payload.otp_code != "123456":
        raise HTTPException(status_code=400, detail="인증번호가 일치하지 않습니다.")

    # 2) 기존 유저인지 확인
    user = db.query(models.User).filter(models.User.phone_number == payload.phone_number).first()
    
    is_registered = False
    access_token = None
    role = None
    
    if user:
        is_registered = True
        access_token = create_access_token(data={"sub": str(user.user_id)})
        role = user.role
    
    return {
        "access_token": access_token or "not_issued",
        "token_type": "bearer",
        "is_registered": is_registered,
        "role": role
    }

# [POST] 시니어 회원가입 (개인정보, 관심사, 활동 거점 등록)

@router.post("/signup/senior", response_model=schemas.SeniorDetailResponse)
def signup_senior(payload: schemas.SeniorCreate, db: Session = Depends(get_db)):
    # 복지관 인증번호 검증
    if payload.auth_code != "SEMO-2026": # 실제로는 DB 조회 권장
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="유효하지 않은 복지관 인증번호입니다."
        )
    
    # 1) 중복 가입 체크
    existing_user = db.query(models.User).filter(models.User.phone_number == payload.phone_number).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="이미 가입된 전화번호입니다.")

    # 2) User 생성
    new_user = models.User(phone_number=payload.phone_number, role="SENIOR")
    db.add(new_user)
    db.flush() 

    # 3) SeniorProfile 생성
    new_profile = models.SeniorProfile(
        user_id=new_user.user_id,
        name=payload.name,
        gender=payload.gender,
        birth_year=payload.birth_year,
        tags=payload.tags,
        bio_summary=payload.bio_summary,
        auth_code=payload.auth_code,
        profile_icon=payload.profile_icon,
    )
    db.add(new_profile)

    # 4) SeniorLocation 생성 (최대 3개 저장)
    for loc in payload.locations:        
        new_location = models.SeniorLocation(
            user_id=new_user.user_id,
            location_name=loc.location_name,
            latitude=loc.latitude,
            longitude=loc.longitude,
            is_primary=loc.is_primary,
        )
        db.add(new_location)

    db.commit()
    db.refresh(new_profile)

    # 4. 토큰 생성 및 반환
    access_token = create_access_token(data={"sub": str(new_user.user_id)})
    
    # DB 객체 조회 및 Pydantic 모델 변환
    db_profile = db.query(models.SeniorProfile).filter(models.SeniorProfile.user_id == new_user.user_id).first()
    result = schemas.SeniorDetailResponse.model_validate(db_profile)
    return result

# 4. 요청자 회원가입 (Requester Signup)
@router.post("/signup/req")
def signup_requester(payload: schemas.RequesterCreate, db: Session = Depends(get_db)):
    # 1) User 테이블 생성
    existing_user = db.query(models.User).filter(models.User.phone_number == payload.phone_number).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="이미 가입된 전화번호입니다.")
    
    new_user = models.User(
        phone_number=payload.phone_number,
        role="REQUESTER"
    )
    db.add(new_user)
    db.flush()

    new_profile = models.RequesterProfile(
        user_id=new_user.user_id,
        nickname=payload.nickname,
        gender=payload.gender,
        birth_year=payload.birth_year
    )
    db.add(new_profile)
    db.commit()
    
    return {
        "access_token": create_access_token(data={"sub": str(new_user.user_id)}),
        "user_id": new_user.user_id
    }

# [GET] 내 프로필 상세 정보 조회 (시니어/요청자 구분)
@router.get("/me", response_model=Union[schemas.SeniorDetailResponse, schemas.RequesterResponse])
def get_my_profile(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 1) 시니어인 경우
    if current_user.role == schemas.UserRole.SENIOR:
        profile = db.query(models.SeniorProfile).filter(models.SeniorProfile.user_id == current_user.user_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="시니어 프로필을 찾을 수 없습니다.")
        profile = db.query(models.SeniorProfile).filter(models.SeniorProfile.user_id == current_user.user_id).first()
        # User 모델에 정의된 locations 관계를 이용해 명시적으로 데이터 할당
        profile.locations = current_user.locations 
        return profile

    # 2) 요청자인 경우
    elif current_user.role == schemas.UserRole.REQUESTER:
        profile = db.query(models.RequesterProfile).filter(models.RequesterProfile.user_id == current_user.user_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="요청자 프로필을 찾을 수 없습니다.")
        return profile

    raise HTTPException(status_code=404, detail="알 수 없는 유저 역할입니다.")

# [PATCH] 내 프로필 정보 및 활동 거점 수정

@router.patch("/me", response_model=Union[schemas.SeniorDetailResponse, schemas.RequesterResponse])
def update_my_profile(
    payload: Union[schemas.SeniorUpdate, schemas.RequesterUpdate], 
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    # 1) 시니어 프로필 업데이트
    if current_user.role == schemas.UserRole.SENIOR:
        profile = db.query(models.SeniorProfile).filter(models.SeniorProfile.user_id == current_user.user_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="프로필을 찾을 수 없습니다.")
        
        update_data = payload.model_dump(exclude_unset=True, exclude={'locations'})
        for key, value in update_data.items():
            setattr(profile, key, value)

        if hasattr(payload, 'locations') and payload.locations is not None:
            db.query(models.SeniorLocation).filter(models.SeniorLocation.user_id == current_user.user_id).delete()
            for loc in payload.locations:
                new_loc = models.SeniorLocation(
                    user_id=current_user.user_id,
                    location_name=loc.location_name,
                    latitude=loc.latitude,
                    longitude=loc.longitude,
                    is_primary=loc.is_primary,
                )
                db.add(new_loc)

        db.commit() 
        db.refresh(profile)
        return profile

    # 2) 요청자 프로필 업데이트
    elif current_user.role == schemas.UserRole.REQUESTER:
        profile = db.query(models.RequesterProfile).filter(models.RequesterProfile.user_id == current_user.user_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="프로필을 찾을 수 없습니다.")
        
        update_data = payload.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(profile, key, value)
            
        db.commit()
        db.refresh(profile)
        return profile

    raise HTTPException(status_code=400, detail="업데이트할 수 없는 유저 유형입니다.")



# [DELETE] 회원 탈퇴 처리 (OTP 인증 후 모든 데이터 삭제)
    # User와 연관된 모든 데이터가 CASCADE로 삭제되도록 설정되어 있습니다.
@router.delete("/me")
def delete_my_profile(payload: schemas.OTPVerify, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.otp_code != "123456":
        raise HTTPException(status_code=400, detail="인증번호가 일치하지 않습니다.")

    db.delete(current_user)
    db.commit()
    return {"message": "회원 탈퇴가 완료되었습니다."}
