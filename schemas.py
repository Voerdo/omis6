from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class CodeGenerationRequest(BaseModel):
    requirements: str
    language: str = "typescript"
    framework: str = "react"
    project_id: Optional[int] = None
    template_id: Optional[int] = None

class CodeGenerationResponse(BaseModel):
    id: int
    requirements: str
    generated_code: str
    language: str
    framework: Optional[str]
    lines_of_code: int
    status: str
    validation_errors: Optional[str] = None
    optimization_suggestions: Optional[str] = None
    created_at: datetime

class TemplateResponse(BaseModel):
    id: int
    name: str
    description: str
    language: str
    category: str
    framework: Optional[str]
    code: str
    downloads: int
    rating: float
    tags: List[str]
    is_public: bool
    creator_id: Optional[int]
    created_at: datetime

class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    status: str
    language: str
    framework: Optional[str]
    lines_of_code: int
    files_count: int
    owner_id: int
    created_at: datetime
    updated_at: datetime

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    role: str
    avatar_url: Optional[str]
    created_at: datetime

class SystemStats(BaseModel):
    total_projects: int
    completed_projects: int
    total_lines_of_code: int
    active_projects: int
    total_templates: int
    total_users: int

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    email: str
    role: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    skills: List[str] = []
    notifications: Dict[str, bool] = {}