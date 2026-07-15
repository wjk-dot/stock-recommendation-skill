from fastapi import APIRouter, HTTPException

from app.config import RECOMMENDATION_DIR
from app.data.recommendation_repository import RecommendationRepository
from app.models import RecommendationSessionCreate


router = APIRouter(prefix="/recommendations")
repository = RecommendationRepository(RECOMMENDATION_DIR)


@router.post("")
def create_recommendation_session(payload: RecommendationSessionCreate):
    session = repository.create(payload)
    return session.model_dump(mode="json")


@router.get("/latest")
def latest_recommendation_session():
    session = repository.get_latest()
    if not session:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "recommendation_session_missing",
                "message": "尚未导入推荐结果。请先由 Skill 生成并发布 recommendations.json。",
            },
        )
    return session.model_dump(mode="json")


@router.get("/{session_id}")
def recommendation_session(session_id: str):
    session = repository.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="未找到该推荐会话")
    return session.model_dump(mode="json")
