"""Admin API — accessible only to users with role='admin'."""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin
from app.models.portfolio import Portfolio
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


class AdminUserItem(BaseModel):
    id: int
    email: str
    name: str
    role: str
    created_at: str
    portfolio_count: int
    age: Optional[int] = None
    risk_tolerance: Optional[str] = None

    model_config = {"from_attributes": True}


@router.get("/users", response_model=List[AdminUserItem])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    users = db.query(User).order_by(User.created_at.desc()).all()
    result = []
    for u in users:
        portfolio_count = (
            db.query(Portfolio).filter(Portfolio.user_id == u.id).count()
        )
        result.append(
            AdminUserItem(
                id=u.id,
                email=u.email,
                name=u.name,
                role=u.role,
                created_at=u.created_at.isoformat() if u.created_at else "",
                portfolio_count=portfolio_count,
                age=u.profile.age if u.profile else None,
                risk_tolerance=u.profile.risk_tolerance if u.profile else None,
            )
        )
    return result


@router.patch("/users/{user_id}/role")
def update_user_role(
    user_id: int,
    body: dict,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Promote or demote a user (admin cannot change their own role)."""
    if user_id == admin.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Cannot change your own role")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")
    new_role = body.get("role")
    if new_role not in ("user", "admin"):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Role must be 'user' or 'admin'")
    user.role = new_role
    db.commit()
    return {"id": user.id, "role": user.role}
