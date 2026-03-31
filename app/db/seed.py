from sqlalchemy.orm import Session
from app import models

def seed_categories(db: Session):
    # 1. 이미 데이터가 있는지 확인 (중복 방지)
    if db.query(models.JobCategory).first():
        print("--- [Seed] Categories already exist. Skipping... ---")
        return

    # 2. 수민님이 정리한 5가지 카테고리 데이터
    categories_data = [
        {
            "main": "가사 및 환경 관리",
            "sub": "반찬/요리, 청소/정리, 쓰레기 배출, 빨래/수선",
            "tags": ["#집밥제조", "#밑반찬", "#장보기대행", "#냉장고정리", "#부분청소", "#분리수거", "#헌옷수거", "#단줄이기"]
        },
        {
            "main": "동행 및 돌봄",
            "sub": "반려동물, 아이 돌봄, 어르신 동행, 등하교 지원",
            "tags": ["#강아지산책", "#고양이케어", "#등하원픽업", "#놀이학습", "#병원동행", "#관공서동행", "#말벗", "#산책친구"]
        },
        {
            "main": "운반 및 심부름",
            "sub": "물건 전달, 구매 대행, 현장 대기, 관리 대행",
            "tags": ["#짐들어주기", "#택배수령", "#약배달", "#줄서기", "#번호표뽑기", "#꽃물주기", "#우편물수거", "#무거운짐"]
        },
        {
            "main": "전문 기술 및 노하우",
            "sub": "간단 집수리, 교육/레슨, 가드닝, 수공예",
            "tags": ["#형광등교체", "#수전교체", "#가구조립", "#한자교육", "#서예", "#전통요리전수", "#화초관리", "#뜨개질"]
        },
        {
            "main": "비즈니스 지원",
            "sub": "홍보 대행, 단기 점포 보조, 단순 사무",
            "tags": ["#전단지배포", "#매장지키기", "#단기알바", "#포장작업", "#주차안내", "#행사보조"]
        }
    ]

    # 3. DB에 삽입
    for data in categories_data:
        new_cat = models.JobCategory(
            main_category=data["main"],
            sub_category=data["sub"],
            tags=data["tags"]
        )
        db.add(new_cat)
    
    try:
        db.commit()
        print("--- [Seed] Job Categories seeded successfully! ---")
    except Exception as e:
        db.rollback()
        print(f"--- [Seed Error] {e} ---")