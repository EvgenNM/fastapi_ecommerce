from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review import ReviewModel
from app.models.project import ProjectModel
from database import get_async_db

router = APIRouter()

@router.put(
    '/{review_id}'
)
async def update_task(
    review_id: int,
    db: AsyncSession = Depends(get_async_db)
) -> dict:
    stmt_review = await db.scalars(
        select(ReviewModel).where(
            ReviewModel.id == review_id,
            ReviewModel.is_active == True
        )
    )
    review = stmt_review.first()
    if review is None:
        raise HTTPException(status_code=404)
        
    stmt_project = await db.scalars(
        select(ProjectModel).where(
            ProjectModel.id == review.project_id,
            ProjectModel.is_active == True
        )
    )
    if stmt_project.first() is None:
        raise HTTPException(status_code=404)
    await db.execute(
        update(ReviewModel)
        .where(ReviewModel.id == review_id)
        .values(ReviewModel.is_active=False)
        )
    await db.commit()
    return {"status": "success", "message": "Review marked as inactive"}