from typing import Optional
import jwt
from fastapi import Depends, Request, HTTPException, Cookie
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import GeneratedCode
from database import get_db, User, SECRET_KEY, ALGORITHM
from services import auth_service
from services import validator
import json

templates = Jinja2Templates(directory="templates")

async def get_current_user(
    db: Session = Depends(get_db),
    access_token: Optional[str] = Cookie(None)
):
    if not access_token:
        return None
    
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
    except jwt.PyJWTError:
        return None
    
    user = db.query(User).filter(User.username == username).first()
    return user

async def get_current_user_dependency(
    current_user: Optional[User] = Depends(get_current_user)
):
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user

async def get_user_context(request: Request, db: Session = Depends(get_db)):
    access_token = request.cookies.get("access_token")
    user = None
    
    if access_token:
        try:
            payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username:
                user = db.query(User).filter(User.username == username).first()
        except jwt.PyJWTError:
            pass
    
    return {"user": user}

async def validate_code_background(db: Session, code_id: int, code: str, language: str): 
    try:
        result = validator.validate(code, language)
        
        
        generated_code = db.query(GeneratedCode).filter(GeneratedCode.id == code_id).first()
        if generated_code:
            generated_code.status = "validated" if result["is_valid"] else "error"
            generated_code.validation_errors = json.dumps(result["errors"]) if result["errors"] else None
            generated_code.optimization_suggestions = json.dumps(result["suggestions"]) if result["suggestions"] else None
            
            db.commit()
    except Exception as e:
        print(f"Ошибка при фоновой валидации: {e}")