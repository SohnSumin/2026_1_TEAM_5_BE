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
from app.utils.ai_tags import extract_senior_tags
from app.db.seed import TAGS_DATA
from app.utils.vector_embedding import get_embedding
import os
import re


load_dotenv()

router = APIRouter(prefix="/api/auth", tags=["auth"])

# app/api/jobs.py
@router.post("/recommend-tags")
def get_recommended_tags(payload: schemas.SeniorTagRecommendRequest):
    # 제목과 본문을 합쳐서 분석
    
    # 1. AI로 서브 태그 추출
    recommended_sub_tags = extract_senior_tags(payload.content)
    
    # 2. 서브 태그에 맞는 메인 태그 매칭
    recommended_main_tags = set()
    for sub in recommended_sub_tags:
        for category in TAGS_DATA:
            if sub in category["sub"]:
                recommended_main_tags.add(category["main"])
                break
                
    return {
        "recommended_main_tags": list(recommended_main_tags),
        "recommended_sub_tags": recommended_sub_tags
    }

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

    # phone_number 정규식 검증 -> 010-2=1234=5678의 형태)
    phone_pattern = re.compile(r"^010-\d{4}-\d{4}$")
    if not phone_pattern.match(payload.phone_number):
        raise HTTPException(status_code=400, detail="전화번호 형식이 올바르지 않습니다. 예시: 010-1234-5678")   

    new_user = models.User(phone_number=payload.phone_number, role="SENIOR")
    db.add(new_user)
    db.flush() 

    # 3) SeniorProfile 생성 (AI 태그 추출 포함)
    final_main_tags = payload.main_tags[0] if payload.main_tags else None
    final_sub_tags = payload.sub_tags if payload.sub_tags else extract_senior_tags(payload.content)

    # 3) Job 생성 (AI 태그 추출 포함)

    # 1. 서브 태그 리스트 준비 (사용자 입력 또는 AI 추출)
    raw_sub_tags = payload.sub_tags if payload.sub_tags else extract_senior_tags(payload.bio_summary)

    # 2. 서브 태그 자체에서도 중복 제거 및 공백 제거
    final_sub_tags = list(set(tag.strip() for tag in raw_sub_tags))

    # 3. 메인 태그 추출 (set을 사용하여 중복 자동 방지)
    final_main_set = set()

    for sub in final_sub_tags:
        for category in TAGS_DATA:
            # 서브 태그가 해당 카테고리에 포함되는지 확인
            if sub in category["sub"]:
                final_main_set.add(category["main"].strip())
                break # 해당 서브 태그의 메인을 찾았으면 다음 서브 태그로 이동

    # 4. 최종 리스트 변환
    final_main_tags = list(final_main_set)

    # 3. 예외 처리 (비어있는지 확인)
    if not final_sub_tags or not final_main_tags:
        raise HTTPException(
            status_code=400, 
            detail="자기소개를 더 자세히 적어주시거나 관심 태그를 선택해주세요."
        )

    new_profile = models.SeniorProfile(
        user_id=new_user.user_id,
        name=payload.name,
        gender=payload.gender,
        birth_year=payload.birth_year,
        main_tags=final_main_tags,
        sub_tags=final_sub_tags,
        gender_preference=payload.gender_preference,
        bio_summary=payload.bio_summary,
        auth_code=payload.auth_code,
        embedding=get_embedding(payload.bio_summary) if payload.bio_summary else None,
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
        gender_preference=payload.gender_preference,
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

        if "bio_summary" in update_data:
            profile.embedding = get_embedding(profile.bio_summary)

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
