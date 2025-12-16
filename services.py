import os
import re
import json
import jwt
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from openai import OpenAI
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, User
from schemas import UserCreate, UserLogin

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = None
OPENAI_AVAILABLE = False

try:
    if OPENAI_API_KEY:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        OPENAI_AVAILABLE = True
        print("OpenAI API подключен")
    else:
        print("OpenAI API ключ не найден")
except Exception as e:
    print(f"Не удалось подключить OpenAI API: {e}")

# Сервис генерации кода
class CodeGeneratorService:
    def __init__(self):
        self.openai_client = openai_client if OPENAI_AVAILABLE else None
    
    def generate_code_with_openai(self, requirements: str, language: str, framework: str) -> Optional[Dict[str, Any]]:
        if not self.openai_client:
            return None
        
        try:
            prompt = f"""Ты - эксперт по программированию. Сгенерируй качественный, рабочий код на языке {language} с использованием фреймворка {framework}.

ТРЕБОВАНИЯ ПОЛЬЗОВАТЕЛЯ:
{requirements}

ИНСТРУКЦИИ:
1. Сгенерируй полный, готовый к использованию код
2. Включи все необходимые импорты/зависимости
3. Добавь комментарии для сложных частей кода
4. Учти лучшие практики для {language} и {framework}
5. Включи базовую обработку ошибок
6. Сделай код модульным и переиспользуемым
7. Если это уместно, добавь типы/интерфейсы
8. Используй современные подходы и паттерны

ВАЖНО: Выведи только чистый код, без пояснений, без ``` в начале и конце."""
            
            print(f"Отправляем запрос к OpenAI API: {language}/{framework}")
            
            response = self.openai_client.responses.create(
                model="gpt-5-nano",
                input=prompt,
                store=True,
            )
            
            if response and response.output_text:
                code = response.output_text.strip()
                code = re.sub(r'^```[\w]*\n', '', code)
                code = re.sub(r'\n```$', '', code)
                
                lines_of_code = len(code.split('\n'))
                
                return {
                    "generated_code": code,
                    "language": language,
                    "framework": framework,
                    "lines_of_code": lines_of_code,
                    "status": "generated",
                    "source": "openai_api"
                }
            
        except Exception as e:
            print(f"Ошибка при генерации через OpenAI: {e}")
            return None
        
        return None
    
    def generate_simple_code(self, requirements: str, language: str, framework: str) -> Dict[str, Any]:
        print(f"Использую простые шаблоны для {language}/{framework}")
        
        code = f"""# Код на {language}
# Фреймворк: {framework}
# Требования: {requirements}

# Реализуйте функциональность согласно требованиям
# 1. Создайте необходимые импорты/зависимости
# 2. Реализуйте основную логику
# 3. Добавьте обработку ошибок
# 4. Протестируйте работу кода"""
        
        lines_of_code = len(code.split('\n'))
        
        return {
            "generated_code": code,
            "language": language,
            "framework": framework,
            "lines_of_code": lines_of_code,
            "status": "generated",
            "source": "simple_templates"
        }
    
    def generate_code(self, requirements: str, language: str = "typescript", framework: str = "react") -> Dict[str, Any]:
        if self.openai_client:
            print(f"Пытаюсь использовать OpenAI API для генерации кода...")
            openai_result = self.generate_code_with_openai(requirements, language, framework)
            
            if openai_result:
                print(f"Код сгенерирован через OpenAI API ({language}/{framework})")
                return openai_result
            else:
                print(f"OpenAI вернул ошибку, использую простые шаблоны")
                return self.generate_simple_code(requirements, language, framework)
        else:
            print(f"OpenAI недоступен, использую простые шаблоны")
            return self.generate_simple_code(requirements, language, framework)

# Валидатор кода
class CodeValidator:
    @staticmethod
    def validate(code: str, language: str) -> Dict[str, Any]:
        errors = []
        warnings = []
        suggestions = []
        
        if not code or len(code.strip()) < 10:
            errors.append("Код слишком короткий или пустой")
        
        if language.lower() == "python":
            try:
                compile(code, '<string>', 'exec')
            except SyntaxError as e:
                errors.append(f"Синтаксическая ошибка Python: {e}")
        
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            if len(line) > 100:
                warnings.append(f"Строка {i} превышает 100 символов")
        
        comment_count = sum(1 for line in lines if line.strip().startswith('#')) if language == "python" else \
                       sum(1 for line in lines if '//' in line or '/*' in line)
        
        if comment_count < 3 and len(lines) > 20:
            suggestions.append("Добавьте комментарии для лучшей читаемости кода")
        
        unique_lines = set(lines)
        if len(lines) - len(unique_lines) > 5:
            warnings.append("Обнаружено дублирование кода")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "suggestions": suggestions
        }

# Сервис аутентификации
class AuthService:
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def register_user(db: Session, user_data: UserCreate):
        existing_user = db.query(User).filter(
            (User.username == user_data.username) | (User.email == user_data.email)
        ).first()
        
        if existing_user:
            raise Exception("Username or email already registered")
        
        user = User(
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name or user_data.username,
            avatar_url=f"https://ui-avatars.com/api/?name={user_data.username}&background=4F46E5&color=fff",
            skills=json.dumps(["JavaScript", "React", "Node.js", "TypeScript"])
        )
        
        user.set_password(user_data.password)
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        return user
    
    @staticmethod
    def authenticate_user(db: Session, username: str, password: str):
        user = db.query(User).filter(User.username == username).first()
        if not user or not user.check_password(password):
            return None
        return user

# Инициализация сервисов
code_generator = CodeGeneratorService()
validator = CodeValidator()
auth_service = AuthService()