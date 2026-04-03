import json
import os
from google.genai import Client
from app.db.seed import ALL_TAGS

# 클라이언트 생성
client = Client(api_key=os.getenv("GEMINI_API_KEY"))

# [MOCK] 시연용 데이터 스위치 (환경변수나 직접 수동 설정 가능)
# 시연 당일 API가 불안정하면 아래를 True로 바꾸세요.
USE_MOCK_AI = os.getenv("USE_MOCK_AI", "False").lower() == "true"

def extract_senior_tags(bio_summary: str) -> list[str]:
    if not bio_summary: return []

    # --- [MOCK CODE START] ---
    if USE_MOCK_AI:
        print("⚠️ [MOCK] 시연용 가짜 태그를 반환합니다.")
        if "요리" in bio_summary or "음식" in bio_summary:
            return ["#집밥제조", "#전통요리전수"]
        if "산책" in bio_summary or "강아지" in bio_summary:
            return ["#강아지산책", "#동물케어"]
        return [ALL_TAGS[0], ALL_TAGS[1]] # 기본값
    # --- [MOCK CODE END] ---

    prompt = f"""
    시니어 인력 매칭 전문가로서 아래 자기소개를 분석해.
    [태그 후보]: {", ".join(ALL_TAGS)}
    반드시 후보 중 관련 있는 태그를 최대 8개 골라 JSON 형식으로 답해: {{"tags": ["#태그1", "#태그2"]}}
    [자기소개]: {bio_summary}
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=prompt
        )
        text = response.text.replace('```json', '').replace('```', '').strip()
        result = json.loads(text)
        return [t for t in result.get("tags", []) if t in ALL_TAGS]
    except Exception as e:
        print(f"AI 시니어 태그 추출 에러: {e}")
        # 에러 발생 시에도 시연이 멈추지 않게 가짜 데이터 반환
        return ["#전통요리전수"] if "요리" in bio_summary else [ALL_TAGS[0]]

def extract_job_post_tag(content: str) -> str:
    if not content: return ""

    # --- [MOCK CODE START] ---
    if USE_MOCK_AI:
        print("⚠️ [MOCK] 시연용 가짜 카테고리를 반환합니다.")
        if "강아지" in content or "산책" in content:
            return "#강아지산책"
        if "병원" in content or "부축" in content:
            return "#병원동행"
        return ALL_TAGS[0]
    # --- [MOCK CODE END] ---
    
    prompt = f"""
    구인 공고 분류기야. 아래 내용을 읽고 후보 중 가장 적합한 태그 하나만 골라.
    [태그 후보]: {", ".join(ALL_TAGS)}
    JSON 형식으로 답해: {{"category": "#태그명"}}
    [공고 내용]: {content}
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=prompt
        )
        text = response.text.replace('```json', '').replace('```', '').strip()
        result = json.loads(text)
        category = result.get("category", "")
        return category if category in ALL_TAGS else ""
    except Exception as e:
        print(f"AI 공고 태그 추출 에러: {e}")
        # 에러 발생 시(429 등) 시연용 기본값 반환
        if "병원" in content: return "#병원동행"
        return ALL_TAGS[0]