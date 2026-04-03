from sqlalchemy.orm import Session
from app import models

TAGS_DATA = [
    {
        "main": "가사 및 환경 관리",
        "sub": ["#집밥제조", "#밑반찬", "#장보기대행", "#냉장고정리", "#부분청소", "#분리수거", "#헌옷수거", "#단줄이기"]
    },
    {
        "main": "동행 및 돌봄",
        "sub": ["#강아지산책", "#고양이케어", "#등하원픽업", "#놀이학습", "#병원동행", "#관공서동행", "#말벗", "#산책친구"]
    },
    {
        "main": "운반 및 심부름",
        "sub": ["#짐들어주기", "#택배수령", "#약배달", "#줄서기", "#번호표뽑기", "#꽃물주기", "#우편물수거", "#무거운짐"]
    },
    {
        "main": "전문 기술 및 노하우",
        "sub": ["#형광등교체", "#수전교체", "#가구조립", "#한자교육", "#서예", "#전통요리전수", "#화초관리", "#뜨개질"]
    },
    {
        "main": "비즈니스 지원",
        "sub": ["#전단지배포", "#매장지키기", "#단기알바", "#포장작업", "#주차안내", "#행사보조"]
    }
]

SUB_TAGS = [tag for cat in TAGS_DATA for tag in cat["sub"]]

def seed_tags(db: Session):
    # 1. 이미 데이터가 있는지 확인 (중복 방지)
    if db.query(models.JobTag).first():
        print("--- [Seed] Tags already exist. Skipping... ---")
        return


    # 2. DB에 삽입
    for data in TAGS_DATA:
        new_tag = models.JobTag(
            main_tag=data["main"],
            sub_tag=data["sub"]
        )
        db.add(new_tag)
    
    try:
        db.commit()
        print("--- [Seed] Job Tags seeded successfully! ---")
    except Exception as e:
        db.rollback()
        print(f"--- [Seed Error] {e} ---")