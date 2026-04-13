---

# 🏆 [2026 제2회 경희대학교 세모톤] 장려상 수상작
> **"지역 복지관 인증 시니어를 위한 AI 기반 하이퍼로컬 소일거리 매칭 플랫폼"**

# 📍 SEENEAR (시니어) - Backend & Infra
시니어의 풍부한 경험을 '안심 에스코트' 및 '생활 보조'라는 가치로 전환하기 위해, **LLM 기반 정형화**와 **벡터 유사도 검색**을 구현한 서버 저장소입니다.

---

## 🏗 Backend Architecture
본 프로젝트는 **FastAPI**를 중심으로 AI 모델과 벡터 데이터베이스를 통합하여, 비정형 데이터를 실시간으로 정형화하고 정밀한 매칭 스코어를 계산하는 구조로 설계되었습니다.



### 🛠 System Stack
* **Framework:** `FastAPI` (Python 3.11), `Uvicorn`
* **Database:** `AWS RDS (PostgreSQL)`
* **Specialized DB Extensions:** * `pgvector`: 시니어-공고 간 시맨틱 유사도 검색
    * `PostGIS`: 지오펜싱(Geofencing) 및 공간 데이터 연산
* **AI Engine:** * `Gemini 1.5 Flash`: 공고문 내 핵심 서비스 태그 자동 추출
    * `SentenceTransformer`: 텍스트 벡터 임베딩 생성
* **Infrastructure:** `Docker` & `Docker-compose`, `AWS (EC2, S3)`

---

## ✨ 핵심 기술 구현 (Core Engineering)

### 1. AI 기반 정밀 태그 추출 (LLM Tagging)
* 사용자가 입력한 자유 형식의 공고문을 분석하여 `[#밤길동행]`, `[#반찬보조]` 등 시스템 정의 태그를 추출하는 파이프라인을 구축했습니다.
* **Gemini 1.5 Flash**를 활용하여 데이터 전처리 없이도 높은 정확도의 카테고리 분류를 수행합니다.

### 2. 시맨틱 유사도 매칭 (Vector Search)
* 시니어의 자기소개(역량)와 구인 공고의 맥락을 벡터화하여 저장합니다.
* **pgvector**를 활용한 코사인 유사도 연산으로 단순 키워드 매칭보다 훨씬 정교한 **'추천 점수순'** 리스트를 제공합니다.

### 3. 실시간 위치 기반 안전 관리 (Spatial API)
* **PostGIS** 공간 쿼리를 통해 시니어의 활동 반경 내 일감만 필터링합니다.
* 지오펜싱 기술을 활용하여 활동 중 이상 이동 경로를 감지할 수 있는 API 기반을 마련했습니다.

---

## 👥 SEENEAR 팀 정보 (Team SEENEAR)

| 역할 | 성함 | 주요 업무 및 기술적 기여 |
| :--- | :--- | :--- |
| **Backend / Infra** | **손수민** | **백엔드 아키텍처 설계 및 API 총괄**, AWS RDS/EC2 인프라 구축, Gemini/Embedding 파이프라인 통합 및 DB 스키마 설계 |
| **AI Engineer** | **송동현** | 시니어 역량-일감 간 **벡터 임베딩 최적화**, 고차원 데이터의 유사도 알고리즘 튜닝 |
| **AI Engineer** | **황정빈** | **Gemini 프롬프트 엔지니어링**, 비정형 데이터 정형화 로직 및 매칭 스코어링 시스템 개발 |
| **Frontend** | **최웅철** | **Flutter 앱 메인 아키텍처**, 역할별(시니어/주민) API 연동 및 복잡한 회원가입/공고 상태 관리 |
| **Frontend** | **김현수** | **Leaflet 기반 위치 시각화**, 실시간 지오펜싱 UI 구현 및 지도 기반 일감 탐색 로직 개발 |
| **UI/UX Design** | **최수현** | 시니어 사용자 중심의 **High-Contrast 인터페이스** 및 지도 시각화 디자인 시스템 구축 |
| **Project Manager** | **홍지욱** | **비즈니스 모델(BM) 수립**, 지역 복지관 파트너십 전략 기획 및 서비스 철학 정의 |

---

## 🚀 실행 가이드 (Server Setup)

### Docker 환경 실행
```bash
# 1. 환경 변수(.env) 설정 후 실행
docker-compose up --build -d

# 2. 서버 상태 확인
curl http://localhost:8000/docs
```

---

**"경험을 가치로, 연결을 안전으로"** SEENEAR 팀은 기술로 세대 간의 벽을 허물고 더 안전한 지역사회를 만듭니다.
