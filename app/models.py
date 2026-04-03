import uuid
from sqlalchemy import Column, String, Integer, Boolean, Text, ForeignKey, DateTime, Date, Time, func, Enum, Float
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from geoalchemy2 import Geography, WKTElement
from app.core.database import Base

# --- 1. Users & Profiles ---

class User(Base):
    __tablename__ = "users"
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number = Column(String(15), unique=True, nullable=False)
    role = Column(String(10), nullable=False) # SENIOR, REQUESTER
    created_at = Column(DateTime, server_default=func.now())

    # 관계 설정
    senior_profile = relationship("SeniorProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    requester_profile = relationship("RequesterProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    locations = relationship("SeniorLocation", back_populates="user", cascade="all, delete-orphan")

class SeniorProfile(Base):
    __tablename__ = "senior_profiles"
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    name = Column(String(50), nullable=False)
    gender = Column(String(10), nullable=False)
    birth_year = Column(Integer, nullable=False)
    profile_icon = Column(String(50))
    trust_score = Column(Integer, default=50)
    badges = Column(ARRAY(Text))
    bio_summary = Column(Text)
    main_tags = Column(ARRAY(String)) # AI가 추출한 주요 대분류 태그 (예: [가사 및 환경 관리])
    sub_tags = Column(ARRAY(String)) # 실제 선택된 태그들 (예: [#밑반찬, #요리])
    auth_code = Column(String(20))
    gender_preference = Column(String(20)) # 남성, 여성, 무관
    embedding = Column(Vector(768))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="senior_profile")

class RequesterProfile(Base):
    __tablename__ = "requester_profiles"
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    nickname = Column(String(50), nullable=False)
    gender = Column(String(10), nullable=False)
    birth_year = Column(Integer, nullable=False)
    trust_score = Column(Integer, default=50)
    updated_at = Column(DateTime, onupdate=func.now())

    user = relationship("User", back_populates="requester_profile")

class SeniorLocation(Base):
    __tablename__ = "senior_locations"
    location_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"))
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    coords = Column(Geography(geometry_type='POINT', srid=4326))
    location_name = Column(Text, nullable=False)
    is_primary = Column(Boolean, default=False)

    user = relationship("User", back_populates="locations")

   # SeniorLocation 내부
    def __init__(self, **kwargs):
        lat = kwargs.get('latitude')
        lon = kwargs.get('longitude')
        if lat is not None and lon is not None:
            # 문자열이 아니라 WKTElement 객체로 감싸서 전달
            kwargs['coords'] = WKTElement(f"POINT({lon} {lat})", srid=4326)
        super().__init__(**kwargs)

# --- 2. Jobs & Matchings ---
class JobPost(Base):
    __tablename__ = "job_posts"
    post_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requester_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    title = Column(String(200), nullable=False)
    content = Column(Text)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    location_coord = Column(Geography(geometry_type='POINT', srid=4326), nullable=False)
    location_name = Column(Text, nullable=False)
    main_tags = Column(ARRAY(String)) # AI가 추출한 주요 대분류 태그 (예: [가사 및 환경 관리])
    sub_tags = Column(ARRAY(String)) # 실제 선택된 태그들 (예: [#밑반찬, #요리])
    thumbnail_url = Column(Text)
    job_date = Column(Date, nullable=False)
    start_time = Column(Time)
    reward = Column(Integer, default=0)
    status = Column(String(20), default="OPEN") # OPEN, MATCHED, DONE, EXPIRED
    embedding = Column(Vector(768))
    created_at = Column(DateTime, server_default=func.now())

    images = relationship("JobImage", back_populates="post", cascade="all, delete-orphan")

    # SeniorLocation 내부
    def __init__(self, **kwargs):
        lat = kwargs.get('latitude')
        lon = kwargs.get('longitude')
        if lat is not None and lon is not None:
            # 문자열이 아니라 WKTElement 객체로 감싸서 전달
            kwargs['location_coord'] = WKTElement(f"POINT({lon} {lat})", srid=4326)
        super().__init__(**kwargs)

class JobImage(Base):
    __tablename__ = "job_images"
    image_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("job_posts.post_id", ondelete="CASCADE"))
    image_url = Column(Text, nullable=False)

    post = relationship("JobPost", back_populates="images")

class Matching(Base):
    __tablename__ = "matchings"
    match_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("job_posts.post_id"))
    senior_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    status = Column(String(20), default="WAITING") # WAITING, ACCEPTED, REJECTED
    proposed_by = Column(String(10), nullable=False) # SENIOR, REQ
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

# --- 3. Notifications & Auth ---

class Notification(Base):
    __tablename__ = "notifications"
    noti_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"))
    related_id = Column(UUID(as_uuid=True)) # match_id 또는 post_id
    type = Column(String(20), nullable=False) # PROPOSAL, ACCEPT, REJECT, JOB
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

class OTPCode(Base):
    __tablename__ = "otp_codes"
    phone_number = Column(String(15), primary_key=True)
    otp_code = Column(String(6), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


# --- 4. User Report ---
class UserReport(Base):
    __tablename__ = "user_reports"
    report_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reporter_user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    reported_user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    reason = Column(ARRAY(Text), nullable=False)
    description = Column(Text)
    status = Column(String(20), default="PENDING") # PENDING, RESOLVED
    created_at = Column(DateTime, server_default=func.now())
