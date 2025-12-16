from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
import json
import jwt
from datetime import datetime, timedelta    
from typing import Optional
from database import SECRET_KEY, ALGORITHM
from database import get_db, User, Project, Template, GeneratedCode
from schemas import (
    CodeGenerationRequest, CodeGenerationResponse, TemplateResponse,
    ProjectResponse, SystemStats, UserResponse, UserCreate, UserLogin,
    UserUpdateRequest, Token
)
from services import code_generator, validator, auth_service
from dependencies import (
    get_current_user, get_current_user_dependency, 
    get_user_context, validate_code_background, templates
)

router = APIRouter()

# API ЭНДПОИНТЫ

@router.post("/api/generate", response_model=CodeGenerationResponse)
async def generate_code(
    request: CodeGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    try:
        result = code_generator.generate_code(
            request.requirements,
            request.language,
            request.framework
        )
        
        generated_code = GeneratedCode(
            requirements=request.requirements,
            generated_code=result["generated_code"],
            language=result["language"],
            framework=result["framework"],
            lines_of_code=result["lines_of_code"],
            status=result["status"],
            user_id=current_user.id,
            project_id=request.project_id,
            template_id=request.template_id
        )
        
        db.add(generated_code)
        db.commit()
        db.refresh(generated_code)
        
        background_tasks.add_task(
            validate_code_background,
            db,
            generated_code.id,
            result["generated_code"],
            result["language"]
        )
        
        return CodeGenerationResponse(
            id=generated_code.id,
            requirements=generated_code.requirements,
            generated_code=generated_code.generated_code,
            language=generated_code.language,
            framework=generated_code.framework,
            lines_of_code=generated_code.lines_of_code,
            status=generated_code.status,
            created_at=generated_code.created_at
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/generated-codes/{code_id}")
async def get_generated_code(
    code_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    generated_code = db.query(GeneratedCode).filter(
        GeneratedCode.id == code_id
    ).first()
    
    if not generated_code:
        raise HTTPException(status_code=404, detail="Генерация не найдена")
    
    if current_user and generated_code.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Нет доступа к этой генерации")
    
    return {
        "id": generated_code.id,
        "requirements": generated_code.requirements,
        "generated_code": generated_code.generated_code,
        "language": generated_code.language,
        "framework": generated_code.framework,
        "lines_of_code": generated_code.lines_of_code,
        "created_at": generated_code.created_at
    }

@router.get("/api/templates", response_model=list[TemplateResponse])
async def get_templates(
    skip: int = 0,
    limit: int = 100,
    language: Optional[str] = None,
    category: Optional[str] = None,
    framework: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Template).filter(Template.is_public == True)
    
    if language:
        query = query.filter(Template.language == language)
    if category:
        query = query.filter(Template.category == category)
    if framework:
        query = query.filter(Template.framework == framework)
    
    templates_list = query.offset(skip).limit(limit).all()
    
    return [
        TemplateResponse(
            id=template.id,
            name=template.name,
            description=template.description,
            language=template.language,
            category=template.category,
            framework=template.framework,
            code=template.code,
            downloads=template.downloads,
            rating=template.rating,
            tags=json.loads(template.tags) if template.tags else [],
            is_public=template.is_public,
            creator_id=template.creator_id,
            created_at=template.created_at
        )
        for template in templates_list
    ]

@router.get("/api/projects", response_model=list[ProjectResponse])
async def get_projects(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    projects = db.query(Project).offset(skip).limit(limit).all()
    
    return [
        ProjectResponse(
            id=project.id,
            name=project.name,
            description=project.description,
            status=project.status,
            language=project.language,
            framework=project.framework,
            lines_of_code=project.lines_of_code,
            files_count=project.files_count,
            owner_id=project.owner_id,
            created_at=project.created_at,
            updated_at=project.updated_at
        )
        for project in projects
    ]

@router.get("/api/stats", response_model=SystemStats)
async def get_stats(db: Session = Depends(get_db)):
    total_projects = db.query(Project).count()
    completed_projects = db.query(Project).filter(Project.status == "completed").count()
    total_lines = db.query(func.sum(Project.lines_of_code)).scalar() or 0
    active_projects = db.query(Project).filter(Project.status == "in_progress").count()
    total_templates = db.query(Template).filter(Template.is_public == True).count()
    total_users = db.query(User).count()
    
    return SystemStats(
        total_projects=total_projects,
        completed_projects=completed_projects,
        total_lines_of_code=total_lines,
        active_projects=active_projects,
        total_templates=total_templates,
        total_users=total_users
    )

@router.post("/api/validate/{code_id}")
async def validate_code(
    code_id: int,
    db: Session = Depends(get_db)
):
    generated_code = db.query(GeneratedCode).filter(GeneratedCode.id == code_id).first()
    if not generated_code:
        raise HTTPException(status_code=404, detail="Код не найден")
    
    result = validator.validate(generated_code.generated_code, generated_code.language)
    
    generated_code.status = "validated" if result["is_valid"] else "error"
    generated_code.validation_errors = json.dumps(result["errors"]) if result["errors"] else None
    generated_code.optimization_suggestions = json.dumps(result["suggestions"]) if result["suggestions"] else None
    
    db.commit()
    
    return result

# Авторизация

@router.post("/api/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    try:
        user = auth_service.register_user(db, user_data)
        
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            avatar_url=user.avatar_url,
            created_at=user.created_at
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/login")
async def login(user_data: UserLogin, response: Response, db: Session = Depends(get_db)):
    user = auth_service.authenticate_user(db, user_data.username, user_data.password)
    
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    access_token = auth_service.create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=30)
    )
    
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=30 * 60,
        samesite="lax",
        secure=False
    )
    
    return {
        "message": "Login successful", 
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "avatar_url": user.avatar_url
        }
    }

@router.post("/api/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token")
    return {"message": "Logout successful"}

@router.get("/api/users/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user_dependency)):
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        avatar_url=current_user.avatar_url,
        created_at=current_user.created_at
    )

@router.post("/api/user/update")
async def update_user(
    request: UserUpdateRequest,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    if request.email != current_user.email:
        existing_user = db.query(User).filter(
            User.email == request.email,
            User.id != current_user.id
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=400, 
                detail="Этот email уже используется другим пользователем"
            )
    
    current_user.full_name = request.full_name or current_user.full_name
    current_user.email = request.email
    current_user.role = request.role
    current_user.avatar_url = request.avatar_url or current_user.avatar_url
    current_user.bio = request.bio or current_user.bio
    current_user.skills = json.dumps(request.skills)
    
    try:
        db.commit()
        db.refresh(current_user)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении: {str(e)}")
    
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "avatar_url": current_user.avatar_url,
        "bio": current_user.bio,
        "skills": request.skills,
        "updated_at": datetime.now()
    }

# Веб-интерфейс

@router.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
    user_context = await get_user_context(request, db)
    
    if user_context["user"]:
        user_generations = db.query(GeneratedCode).filter(GeneratedCode.user_id == user_context["user"].id).all()
        stats = {
            "total_generations": len(user_generations),
            "total_lines": sum(g.lines_of_code for g in user_generations)
        }
    else:
        stats = {
            "total_generations": db.query(GeneratedCode).count(),
            "total_lines": db.query(func.sum(GeneratedCode.lines_of_code)).scalar() or 0
        }
    
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            **user_context,
            "stats": stats
        }
    )

@router.get("/generator", response_class=HTMLResponse)
async def generator_page(request: Request, db: Session = Depends(get_db)):
    user_context = await get_user_context(request, db)
    languages = ["TypeScript", "JavaScript", "Python", "Java", "C#", "Go"]
    frameworks = ["React", "Vue", "Angular", "Express", "Django", "Spring", "FastAPI", ".NET"]
    
    return templates.TemplateResponse(
        "generator.html",
        {
            "request": request,
            **user_context,
            "languages": languages,
            "frameworks": frameworks
        }
    )

@router.get("/templates", response_class=HTMLResponse)
async def templates_page(request: Request, db: Session = Depends(get_db)):
    user_context = await get_user_context(request, db)
    templates_list = db.query(Template).filter(Template.is_public == True).all()
    categories = list(set([t.category for t in templates_list if t.category]))
    languages = list(set([t.language for t in templates_list]))
    
    return templates.TemplateResponse(
        "templates.html",
        {
            "request": request,
            **user_context,
            "templates": templates_list,
            "categories": categories,
            "languages": languages,
            "selected_category": "all",
            "selected_language": "all"
        }
    )

@router.get("/projects", response_class=HTMLResponse)
async def projects_page(request: Request, db: Session = Depends(get_db)):
    user_context = await get_user_context(request, db)
    
    if not user_context["user"]:
        return RedirectResponse(url="/login")
    
    generations = db.query(GeneratedCode).filter(
        GeneratedCode.user_id == user_context["user"].id
    ).order_by(GeneratedCode.created_at.desc()).all()
    
    total_generations = len(generations)
    
    return templates.TemplateResponse(
        "projects.html",
        {
            "request": request,
            **user_context,
            "generations": generations,
            "total_generations": total_generations
        }
    )

@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, db: Session = Depends(get_db)):
    access_token = request.cookies.get("access_token")
    user = None
    
    if access_token:
        try:
            payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username:
                user = db.query(User).filter(User.username == username).first()
        except:
            return RedirectResponse(url="/login")
    
    if not user:
        return RedirectResponse(url="/login")
    
    user_generations = db.query(GeneratedCode).filter(
        GeneratedCode.user_id == user.id
    ).all()
    
    user_stats = {
        "total_generations": len(user_generations),
        "total_lines": sum(g.lines_of_code for g in user_generations) if user_generations else 0,
        "join_date": user.created_at.strftime("%d.%m.%Y")
    }
    
    recent_generations = db.query(GeneratedCode).filter(
        GeneratedCode.user_id == user.id
    ).order_by(GeneratedCode.created_at.desc()).limit(5).all()
    
    user_skills = json.loads(user.skills) if user.skills else ["JavaScript", "React", "Node.js", "TypeScript", "Python"]
    
    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "avatar_url": user.avatar_url,
                "created_at": user.created_at,
                "bio": user.bio
            },
            "user_skills": user_skills,
            "user_stats": user_stats,
            "recent_generations": recent_generations
        }
    )

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {"request": request}
    )

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(
        "register.html",
        {"request": request}
    )