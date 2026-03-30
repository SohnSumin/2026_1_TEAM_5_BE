from pydantic import BaseModel, Field, EmailStr, HttpUrl
from typing import List, Optional
from uuid import UUID
from datetime import date, time, datetime
from enum import Enum

# --- 공통 Enums ---
class UserRole(str, Enum):
    SENIOR = "SENIOR"
    REQUESTER = "REQUESTER"

class MatchStatus(str, Enum):
    WAITING = "WAITING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"

class JobStatus(str, Enum):
    OPEN = "OPEN"
    MATCHED = "MATCHED"
    DONE = "DONE"
    EXPIRED = "EXPIRED"

# --- 1. Auth & Profiles ---

class Token(BaseModel):
    access_token: str
    token_type: str
    is_registered: bool
    role: Optional[UserRole] = None

# OTP 인증

class OTPRequest(BaseModel):
    phone_number: str = Field(..., example="01012345678")

class OTPVerify(BaseModel):
    phone_number: str = Field(..., example="01012345678")
    otp_code: str = Field(..., example="123456")

# 로그인응답

class LoginRequest(BaseModel):
    phone_number: str
    otp_code: str

class LoginResponse(BaseModel):
    access_token: str
    is_registered: bool
    role: Optional[UserRole] = None

# 위치 정보 기본 구조 (위경도)
class LocationBase(BaseModel):
    location_name: str
    latitude: float
    longitude: float
    is_primary: Optional[bool] = False

class LocationCreate(LocationBase):
    pass

class LocationResponse(LocationBase):
    location_id: UUID

    class Config:
        from_attributes = True

# 시니어 가입/수정
class SeniorCreate(BaseModel):
    phone_number: str
    name: str
    gender: str
    birth_year: int
    auth_code: Optional[str] = None
    profile_icon: Optional[str] = "default_icon"
    locations: List[LocationCreate] = Field(..., min_items=1, max_items=3)

class SeniorUpdate(BaseModel):
    name: Optional[str] = None
    profile_image_url: Optional[str] = None
    birth_year: Optional[int] = None
    bio_summary: Optional[str] = None
    profile_icon: Optional[str] = None
    locations: Optional[List[LocationCreate]] = None

# 시니어 상세 응답 (위치 정보 포함)
class SeniorDetailResponse(BaseModel):
    user_id: UUID
    name: str
    gender: str
    birth_year: int
    trust_score: int = 50
    profile_icon: Optional[str] = None 
    bio_summary: Optional[str] = None
    locations: List[LocationResponse] = []

    class Config:
        from_attributes = True

# 요청자 가입/수정
class RequesterCreate(BaseModel):
    phone_number: str
    nickname: str
    gender: str
    birth_year: int

class RequesterResponse(BaseModel):
    user_id: UUID
    nickname: str
    profile_image_url: Optional[str] = None
    trust_score: int

    class Config:
        from_attributes = True

# --- 2. Job Posts ---

class JobPostCreate(BaseModel):
    title: str
    content: str
    category_tag: str
    job_date: date
    start_time: time
    latitude: float
    longitude: float
    location_name: str
    reward: int = 0
    image_urls: List[str] = []

class JobPostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    status: Optional[JobStatus] = None

class JobPostResponse(BaseModel):
    post_id: UUID
    requester_id: UUID
    title: str
    category_tag: str
    job_date: date
    location_name: str
    thumbnail_url: Optional[str]
    status: JobStatus
    created_at: datetime

    class Config:
        from_attributes = True

class JobPostDetailResponse(JobPostResponse):
    content: str
    latitude: float
    longitude: float
    reward: int
    image_urls: List[str] = []

# --- 3. Matchings & Notifications ---

class MatchApplyRequest(BaseModel):
    post_id: UUID

class MatchProposeRequest(BaseModel):
    post_id: UUID
    senior_id: UUID

class MatchStatusUpdate(BaseModel):
    status: MatchStatus

class NotificationResponse(BaseModel):
    noti_id: UUID
    type: str
    content: str
    related_id: UUID
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True