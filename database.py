from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float, inspect, text
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy.orm import Session
from datetime import datetime
import hashlib
import secrets
import json
import os

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

SQLALCHEMY_DATABASE_URL = "sqlite:///./codegen.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Функция для получения сессии БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Модели
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(100))
    role = Column(String(50), default="developer")
    avatar_url = Column(String(500), default="https://ui-avatars.com/api/?name=User&background=4F46E5&color=fff")
    hashed_password = Column(String(255), nullable=True)
    skills = Column(Text, default='["JavaScript", "React", "Node.js"]')
    created_at = Column(DateTime, default=datetime.now)
    is_active = Column(Boolean, default=True)
    bio = Column(Text)
    
    projects = relationship("Project", back_populates="owner")
    generated_codes = relationship("GeneratedCode", back_populates="user")
    
    def set_password(self, password: str):
        if len(password) > 50:
            password = password[:50]
        salt = secrets.token_hex(8)
        self.hashed_password = f"{salt}:{hashlib.sha256((password + salt).encode()).hexdigest()}"
    
    def check_password(self, password: str) -> bool:
        if not self.hashed_password:
            return False
        try:
            salt, stored_hash = self.hashed_password.split(':')
            if len(password) > 50:
                password = password[:50]
            return hashlib.sha256((password + salt).encode()).hexdigest() == stored_hash
        except:
            return False

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="in_progress")
    language = Column(String(50), default="typescript")
    framework = Column(String(100))
    lines_of_code = Column(Integer, default=0)
    files_count = Column(Integer, default=0)
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    owner = relationship("User", back_populates="projects")
    generated_codes = relationship("GeneratedCode", back_populates="project")

class Template(Base):
    __tablename__ = "templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    language = Column(String(50), nullable=False)
    category = Column(String(100))
    framework = Column(String(100))
    code = Column(Text, nullable=False)
    downloads = Column(Integer, default=0)
    rating = Column(Float, default=0.0)
    tags = Column(Text)
    is_public = Column(Boolean, default=True)
    creator_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.now)
    
    creator = relationship("User")

class GeneratedCode(Base):
    __tablename__ = "generated_codes"
    
    id = Column(Integer, primary_key=True, index=True)
    requirements = Column(Text, nullable=False)
    generated_code = Column(Text, nullable=False)
    language = Column(String(50), nullable=False)
    framework = Column(String(100))
    lines_of_code = Column(Integer, default=0)
    status = Column(String(50), default="generated")
    validation_errors = Column(Text)
    optimization_suggestions = Column(Text)
    user_id = Column(Integer, ForeignKey("users.id"))
    project_id = Column(Integer, ForeignKey("projects.id"))
    template_id = Column(Integer, ForeignKey("templates.id"))
    created_at = Column(DateTime, default=datetime.now)
    
    user = relationship("User", back_populates="generated_codes")
    project = relationship("Project", back_populates="generated_codes")
    template = relationship("Template")

def check_and_add_columns():
    inspector = inspect(engine)
    if 'users' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('users')]
        
        if 'hashed_password' not in columns:
            print("Добавляем столбец hashed_password в таблицу users...")
            with engine.connect() as conn:
                conn.execute(text('ALTER TABLE users ADD COLUMN hashed_password VARCHAR(255)'))
                conn.commit()
        
        if 'bio' not in columns:
            print("Добавляем столбец bio в таблицу users...")
            with engine.connect() as conn:
                conn.execute(text('ALTER TABLE users ADD COLUMN bio TEXT'))
                conn.commit()

def init_demo_data():
    from sqlalchemy.orm import Session
    import json
    
    check_and_add_columns()
    
    db = SessionLocal()
    try:   
        if db.query(Template).count() == 0:
            print("Создаю демо-шаблоны...")
            
            demo_user_id = db.query(User.id).first()[0]
            
            demo_templates = [
                Template(
                    name="REST API контроллер",
                    description="Базовый REST API контроллер с CRUD операциями",
                    language="TypeScript",
                    category="backend",
                    framework="NextJS",
                    code="""import { Controller, Get, Post, Put, Delete, Body, Param } from '@nestjs/common';

@Controller('items')
export class ItemsController {
  private items = [];
  private idCounter = 1;

  @Get()
  findAll() {
    return this.items;
  }

  @Get(':id')
  findOne(@Param('id') id: string) {
    const item = this.items.find(item => item.id === parseInt(id));
    if (!item) {
      throw new Error('Item not found');
    }
    return item;
  }

  @Post()
  create(@Body() itemData: any) {
    const newItem = {
      id: this.idCounter++,
      ...itemData,
      createdAt: new Date()
    };
    this.items.push(newItem);
    return newItem;
  }

  @Put(':id')
  update(@Param('id') id: string, @Body() itemData: any) {
    const index = this.items.findIndex(item => item.id === parseInt(id));
    if (index === -1) {
      throw new Error('Item not found');
    }
    this.items[index] = { ...this.items[index], ...itemData, updatedAt: new Date() };
    return this.items[index];
  }

  @Delete(':id')
  remove(@Param('id') id: string) {
    const index = this.items.findIndex(item => item.id === parseInt(id));
    if (index === -1) {
      throw new Error('Item not found');
    }
    const deletedItem = this.items.splice(index, 1)[0];
    return { message: 'Item deleted', item: deletedItem };
  }
}""",
                    downloads=1245,
                    rating=4.8,
                    tags=json.dumps(["TypeScript", "NextJS", "backend", "api", "crud"]),
                    creator_id=demo_user_id
                ),
                
                Template(
                    name="Форма с валидацией",
                    description="React компонент формы с полной валидацией полей",
                    language="TypeScript",
                    category="frontend",
                    framework="React",
                    code="""import React, { useState } from 'react';
import { useForm, SubmitHandler } from 'react-hook-form';

interface FormData {
  email: string;
  password: string;
  confirmPassword: string;
  agreeToTerms: boolean;
}

const RegistrationForm: React.FC = () => {
  const { register, handleSubmit, watch, formState: { errors } } = useForm<FormData>();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitMessage, setSubmitMessage] = useState('');

  const onSubmit: SubmitHandler<FormData> = async (data) => {
    setIsSubmitting(true);
    try {
      // Имитация запроса к API
      await new Promise(resolve => setTimeout(resolve, 1000));
      setSubmitMessage('Регистрация успешно завершена!');
      console.log('Отправленные данные:', data);
    } catch (error) {
      setSubmitMessage('Ошибка при регистрации');
      console.error(error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const password = watch('password');

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="registration-form">
      <div className="form-group">
        <label htmlFor="email">Email</label>
        <input
          id="email"
          type="email"
          {...register('email', {
            required: 'Email обязателен',
            pattern: {
              value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,}$/i,
              message: 'Неверный формат email'
            }
          })}
          className={errors.email ? 'error' : ''}
        />
        {errors.email && <span className="error-message">{errors.email.message}</span>}
      </div>

      <div className="form-group">
        <label htmlFor="password">Пароль</label>
        <input
          id="password"
          type="password"
          {...register('password', {
            required: 'Пароль обязателен',
            minLength: {
              value: 6,
              message: 'Пароль должен быть не менее 6 символов'
            }
          })}
          className={errors.password ? 'error' : ''}
        />
        {errors.password && <span className="error-message">{errors.password.message}</span>}
      </div>

      <div className="form-group">
        <label htmlFor="confirmPassword">Подтверждение пароля</label>
        <input
          id="confirmPassword"
          type="password"
          {...register('confirmPassword', {
            required: 'Подтвердите пароль',
            validate: value => value === password || 'Пароли не совпадают'
          })}
          className={errors.confirmPassword ? 'error' : ''}
        />
        {errors.confirmPassword && (
          <span className="error-message">{errors.confirmPassword.message}</span>
        )}
      </div>

      <div className="form-group checkbox">
        <input
          id="agreeToTerms"
          type="checkbox"
          {...register('agreeToTerms', {
            required: 'Необходимо согласие с условиями'
          })}
        />
        <label htmlFor="agreeToTerms">Согласен с условиями использования</label>
        {errors.agreeToTerms && (
          <span className="error-message">{errors.agreeToTerms.message}</span>
        )}
      </div>

      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Отправка...' : 'Зарегистрироваться'}
      </button>

      {submitMessage && <div className="submit-message">{submitMessage}</div>}
    </form>
  );
};

export default RegistrationForm;""",
                    downloads=2103,
                    rating=4.9,
                    tags=json.dumps(["TypeScript", "React", "frontend", "form", "validation"]),
                    creator_id=demo_user_id
                ),
                
                Template(
                    name="Аутентификация JWT",
                    description="Middleware для проверки JWT токенов в Express.js",
                    language="JavaScript",
                    category="auth",
                    framework="Express",
                    code="""const jwt = require('jsonwebtoken');
const { promisify } = require('util');

const JWT_SECRET = process.env.JWT_SECRET || 'your-secret-key-change-in-production';
const JWT_EXPIRES_IN = process.env.JWT_EXPIRES_IN || '24h';

// Генерация JWT токена
const generateToken = (userId, userRole = 'user') => {
  return jwt.sign(
    { id: userId, role: userRole },
    JWT_SECRET,
    { expiresIn: JWT_EXPIRES_IN }
  );
};

// Middleware для проверки JWT
const authMiddleware = async (req, res, next) => {
  try {
    // 1. Проверяем наличие токена
    let token;
    if (req.headers.authorization && req.headers.authorization.startsWith('Bearer')) {
      token = req.headers.authorization.split(' ')[1];
    }

    if (!token) {
      return res.status(401).json({
        success: false,
        message: 'Вы не авторизованы. Пожалуйста, войдите в систему.'
      });
    }

    // 2. Верификация токена
    const decoded = await promisify(jwt.verify)(token, JWT_SECRET);

    // 3. Добавляем информацию о пользователе в запрос
    req.user = decoded;
    next();
  } catch (error) {
    if (error.name === 'JsonWebTokenError') {
      return res.status(401).json({
        success: false,
        message: 'Недействительный токен. Пожалуйста, войдите снова.'
      });
    }

    if (error.name === 'TokenExpiredError') {
      return res.status(401).json({
        success: false,
        message: 'Срок действия токена истек. Пожалуйста, войдите снова.'
      });
    }

    return res.status(500).json({
        success: false,
        message: 'Ошибка при проверке авторизации'
    });
  }
};

// Middleware для проверки ролей
const restrictTo = (...roles) => {
  return (req, res, next) => {
    if (!req.user) {
      return res.status(401).json({
        success: false,
        message: 'Вы не авторизованы'
      });
    }

    if (!roles.includes(req.user.role)) {
      return res.status(403).json({
        success: false,
        message: 'У вас нет прав для выполнения этого действия'
      });
    }

    next();
  };
};

// Пример использования в роутере
const router = require('express').Router();

// Защищенный маршрут
router.get('/profile', authMiddleware, async (req, res) => {
  try {
    // Здесь можно получить данные пользователя из БД
    const user = {
      id: req.user.id,
      role: req.user.role
    };

    res.status(200).json({
      success: true,
      data: user
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      message: 'Ошибка при получении профиля'
    });
  }
});

// Маршрут только для администраторов
router.get('/admin', authMiddleware, restrictTo('admin'), (req, res) => {
  res.status(200).json({
    success: true,
    message: 'Добро пожаловать в админ-панель'
  });
});

module.exports = {
  generateToken,
  authMiddleware,
  restrictTo
};""",
                    downloads=1867,
                    rating=4.8,
                    tags=json.dumps(["JavaScript", "Express", "auth", "jwt", "security"]),
                    creator_id=demo_user_id
                )
            ]
            
            for template in demo_templates:
                db.add(template)
            
            db.commit()
            print(f"Создано {len(demo_templates)} демо-шаблонов")
            
    except Exception as e:
        print(f"Ошибка при инициализации демо-данных: {e}")
        db.rollback()
    finally:
        db.close()