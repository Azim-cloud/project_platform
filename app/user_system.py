from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text, or_, ForeignKey, desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from jose import jwt
from datetime import datetime, timedelta
import hashlib
import secrets

# ==================== БАЗА ДАННЫХ ====================
DATABASE_URL = "sqlite:///./projects.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    full_name = Column(String, default="")
    hashed_password = Column(String)
    role = Column(String, default="user")
    is_active = Column(Boolean, default=True)
    reset_token = Column(String, nullable=True)
    reset_token_expires = Column(String, nullable=True)
    created_at = Column(String, default=str(datetime.now()))
    updated_at = Column(String, default=str(datetime.now()))
    
    projects = relationship("Project", back_populates="owner")
    notifications = relationship("Notification", back_populates="user")
    comments = relationship("Comment", back_populates="user")

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True)
    name = Column(String, index=True)
    description = Column(Text, default="")
    status = Column(String, default="active")
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(String, default=str(datetime.now()))
    updated_at = Column(String, default=str(datetime.now()))
    
    owner = relationship("User", back_populates="projects")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    title = Column(String, index=True)
    description = Column(Text, default="")
    status = Column(String, default="todo")
    priority = Column(String, default="medium")
    deadline = Column(String, nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    created_by = Column(Integer, ForeignKey("users.id"))
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(String, default=str(datetime.now()))
    updated_at = Column(String, default=str(datetime.now()))
    
    project = relationship("Project", back_populates="tasks")
    creator = relationship("User", foreign_keys=[created_by])
    assignee = relationship("User", foreign_keys=[assigned_to])
    comments = relationship("Comment", back_populates="task", cascade="all, delete-orphan")

class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(String, default=str(datetime.now()))
    
    task = relationship("Task", back_populates="comments")
    user = relationship("User", back_populates="comments")

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    message = Column(Text)
    type = Column(String, default="info")
    is_read = Column(Boolean, default=False)
    link = Column(String, nullable=True)
    created_at = Column(String, default=str(datetime.now()))
    
    user = relationship("User", back_populates="notifications")

class ActivityLog(Base):
    __tablename__ = "activity_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String)
    details = Column(Text)
    task_id = Column(Integer, nullable=True)
    project_id = Column(Integer, nullable=True)
    created_at = Column(String, default=str(datetime.now()))

Base.metadata.create_all(bind=engine)

# ==================== СОЗДАНИЕ АДМИНА ====================
def create_first_admin(db: Session):
    if db.query(User).count() == 0:
        admin = User(
            username="admin",
            email="admin@admin.com",
            full_name="Administrator",
            hashed_password=hash_password("admin123"),
            role="admin"
        )
        db.add(admin)
        db.commit()
        print("✅ Администратор создан: admin / admin123")

# ==================== ПРИЛОЖЕНИЕ ====================
app = FastAPI()
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    return salt + ":" + hashlib.sha256((salt + password).encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        salt, hash_value = hashed_password.split(":")
        return hash_value == hashlib.sha256((salt + plain_password).encode()).hexdigest()
    except:
        return False

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=1)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        return db.query(User).filter(User.username == username).first()
    except:
        return None

def generate_reset_token() -> str:
    return secrets.token_urlsafe(32)

def add_notification(user_id: int, title: str, message: str, type: str = "info", link: str = None, db: Session = None):
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=type,
        link=link
    )
    db.add(notification)
    db.commit()

def add_activity(user_id: int, action: str, details: str, task_id: int = None, project_id: int = None, db: Session = None):
    activity = ActivityLog(
        user_id=user_id,
        action=action,
        details=details,
        task_id=task_id,
        project_id=project_id
    )
    db.add(activity)
    db.commit()

def is_admin(user):
    return user and user.role == "admin"

# ==================== МОБИЛЬНЫЙ CSS ====================
BASE_STYLE = """
<style>
    * { box-sizing: border-box; }
    body { 
        font-size: 16px; 
        padding-bottom: 20px; 
        background: #f0f2f5; 
        min-height: 100vh;
    }
    .container { max-width: 1200px; }
    
    /* === ОБЩИЕ СТИЛИ === */
    .card { 
        margin-bottom: 20px; 
        border-radius: 12px; 
        border: none; 
        box-shadow: 0 2px 10px rgba(0,0,0,0.08); 
        background: #fff;
    }
    .card-header { 
        padding: 15px 20px; 
        border-radius: 12px 12px 0 0 !important; 
        font-weight: 600; 
    }
    .card-body { padding: 20px; }
    
    .btn { 
        padding: 10px 20px; 
        font-size: 15px; 
        border-radius: 8px; 
        min-height: 44px; 
        display: inline-flex; 
        align-items: center; 
        justify-content: center; 
        gap: 8px; 
        transition: all 0.2s;
    }
    .btn:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
    .btn-sm { padding: 6px 12px; font-size: 13px; min-height: 34px; }
    .btn-block { width: 100%; display: flex; }
    
    .form-control, .form-select { 
        padding: 10px 14px; 
        font-size: 15px; 
        border-radius: 8px; 
        min-height: 44px; 
        border: 1px solid #ddd; 
        transition: border-color 0.2s, box-shadow 0.2s;
    }
    .form-control:focus, .form-select:focus { 
        border-color: #0d6efd; 
        box-shadow: 0 0 0 4px rgba(13,110,253,0.12); 
    }
    textarea.form-control { min-height: 80px; resize: vertical; }
    
    /* === НАВИГАЦИЯ === */
    .navbar { padding: 10px 0; }
    .navbar-brand { font-size: 20px; font-weight: 700; }
    .navbar-nav .nav-link { padding: 8px 16px; font-size: 15px; }
    
    /* === ЗАГОЛОВКИ === */
    h1 { font-size: 28px; font-weight: 700; }
    h2 { font-size: 22px; font-weight: 600; }
    h3 { font-size: 19px; font-weight: 600; }
    h4 { font-size: 17px; font-weight: 600; }
    h5 { font-size: 16px; font-weight: 600; }
    h6 { font-size: 15px; font-weight: 600; }
    
    /* === КАРТОЧКИ СТАТИСТИКИ === */
    .stat-card { 
        border-radius: 12px; 
        padding: 15px; 
        transition: transform 0.2s, box-shadow 0.2s;
        cursor: default;
    }
    .stat-card:hover { 
        transform: translateY(-4px); 
        box-shadow: 0 8px 25px rgba(0,0,0,0.12);
    }
    .stat-card h2 { font-size: 32px; margin: 0; }
    .stat-card p { font-size: 14px; margin: 0; opacity: 0.9; }
    
    /* === ТАБЛИЦЫ === */
    .table-responsive { border-radius: 8px; overflow-x: auto; }
    .table { font-size: 14px; margin: 0; }
    .table td, .table th { padding: 10px 12px; vertical-align: middle; }
    .table-hover tbody tr:hover { background-color: rgba(13,110,253,0.04); }
    
    /* === БЕЙДЖИ === */
    .badge { font-size: 12px; padding: 4px 12px; border-radius: 20px; }
    
    /* === МОДАЛКА === */
    .modal-content { border-radius: 16px; }
    .modal-header { padding: 16px 20px; border-radius: 16px 16px 0 0; }
    .modal-body { padding: 20px; }
    .modal-footer { padding: 16px 20px; }
    
    /* === УВЕДОМЛЕНИЯ === */
    .notification-item { padding: 12px 16px; margin-bottom: 10px; border-radius: 10px; }
    
    /* === АНИМАЦИИ === */
    .fade-in { animation: fadeIn 0.3s ease; }
    @keyframes fadeIn { 
        from { opacity: 0; transform: translateY(12px); } 
        to { opacity: 1; transform: translateY(0); } 
    }
    .task-card { transition: transform 0.2s, box-shadow 0.2s; }
    .task-card:hover { transform: translateY(-3px); box-shadow: 0 6px 20px rgba(0,0,0,0.08); }
    
    /* === ОТСТУПЫ === */
    .mt-4 { margin-top: 20px !important; }
    .mb-4 { margin-bottom: 20px !important; }
    .mt-3 { margin-top: 16px !important; }
    .mb-3 { margin-bottom: 16px !important; }
    .mt-2 { margin-top: 10px !important; }
    .mb-2 { margin-bottom: 10px !important; }
    .gap-2 { gap: 10px !important; }
    
    /* === СТИЛИ ДЛЯ ПК (ширина > 768px) === */
    @media (min-width: 769px) {
        .project-grid .col-md-6 { padding: 8px; }
        .task-grid .col-md-4, .task-grid .col-md-6 { padding: 8px; }
        
        .form-control, .form-select { padding: 8px 12px; min-height: 38px; font-size: 14px; }
        .btn { padding: 8px 18px; min-height: 38px; font-size: 14px; }
        .btn-sm { padding: 4px 10px; min-height: 30px; font-size: 12px; }
        
        .card-body { padding: 16px; }
        .card-header { padding: 12px 16px; }
        
        .stat-cards .col-md-3 { padding: 6px; }
        .stat-card h2 { font-size: 28px; }
        
        .table { font-size: 13px; }
        .table td, .table th { padding: 8px 12px; }
        
        h1 { font-size: 24px; }
        h2 { font-size: 20px; }
        
        .navbar-nav { flex-direction: row; }
        .navbar-nav .nav-link { padding: 6px 14px; font-size: 14px; }
        
        .admin-stats .col-md-3 { padding: 6px; }
        .admin-stats .stat-card { padding: 12px; }
        .admin-stats .stat-card h2 { font-size: 26px; }
    }
    
    /* === СТИЛИ ДЛЯ ТЕЛЕФОНА (ширина ≤ 768px) === */
    @media (max-width: 768px) {
        .container { padding-left: 12px; padding-right: 12px; }
        .card { margin-bottom: 14px; border-radius: 10px; }
        .card-header { padding: 12px 14px; font-size: 14px; }
        .card-body { padding: 14px; }
        
        .btn { 
            padding: 11px 16px; 
            font-size: 15px; 
            min-height: 46px; 
            border-radius: 10px; 
            width: 100%;
        }
        .btn-sm { padding: 7px 10px; font-size: 13px; min-height: 34px; width: auto; }
        .btn-group .btn { flex: 1; padding: 8px 6px; font-size: 12px; min-height: 34px; width: auto; }
        
        .form-control, .form-select { 
            padding: 11px 14px; 
            font-size: 15px; 
            min-height: 46px; 
            border-radius: 10px; 
        }
        textarea.form-control { min-height: 80px; }
        
        .navbar-brand { font-size: 18px; }
        .navbar-toggler { padding: 6px 10px; border: none; }
        .navbar-nav .nav-link { padding: 10px 12px; font-size: 15px; text-align: center; }
        
        h1 { font-size: 22px; }
        h2 { font-size: 19px; }
        h3 { font-size: 17px; }
        h4 { font-size: 16px; }
        h5 { font-size: 15px; }
        h6 { font-size: 14px; }
        
        .row { margin: 0 -5px; }
        .row > * { padding: 0 5px; }
        
        .project-grid .col-12, .task-grid .col-12 { padding: 5px; }
        
        .stat-cards .col-6 { padding: 4px; }
        .stat-card { padding: 10px; border-radius: 10px; }
        .stat-card h2 { font-size: 22px; }
        .stat-card p { font-size: 11px; }
        .stat-card h5 { font-size: 14px; margin: 0; }
        
        .table-responsive { border-radius: 8px; overflow-x: auto; }
        .table { font-size: 13px; }
        .table td, .table th { padding: 6px 8px; white-space: nowrap; }
        
        .modal-content { border-radius: 14px; margin: 10px; }
        .modal-header { padding: 14px; }
        .modal-body { padding: 14px; }
        .modal-footer { padding: 12px 14px; flex-wrap: wrap; }
        .modal-footer .btn { flex: 1; min-width: 80px; }
        
        .notification-item { padding: 10px 12px; margin-bottom: 8px; border-radius: 8px; }
        
        .mt-4 { margin-top: 14px !important; }
        .mb-4 { margin-bottom: 14px !important; }
        .mt-3 { margin-top: 12px !important; }
        .mb-3 { margin-bottom: 12px !important; }
        .mt-2 { margin-top: 8px !important; }
        .mb-2 { margin-bottom: 8px !important; }
        .gap-2 { gap: 6px !important; }
        
        .fade-in { animation: fadeIn 0.25s ease; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
    }
    
    /* === МАЛЕНЬКИЕ ТЕЛЕФОНЫ (≤ 400px) === */
    @media (max-width: 400px) {
        .btn { font-size: 13px; padding: 8px 12px; min-height: 38px; }
        .form-control, .form-select { font-size: 14px; padding: 8px 12px; min-height: 38px; }
        .table { font-size: 11px; }
        .table td, .table th { padding: 4px 6px; }
        .badge { font-size: 10px; padding: 2px 8px; }
        .stat-card h2 { font-size: 18px; }
        h1 { font-size: 18px; }
        h2 { font-size: 16px; }
        .navbar-brand { font-size: 15px; }
    }
</style>
"""

# ==================== HTML СТРАНИЦЫ ====================

REGISTER_PAGE = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Регистрация</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    {BASE_STYLE}
</head>
<body class="bg-light">
    <div class="container mt-4">
        <div class="row justify-content-center">
            <div class="col-12 col-sm-10 col-md-6 col-lg-5">
                <div class="card card-shadow fade-in">
                    <div class="card-header bg-primary text-white text-center">
                        <h5 class="mb-0"><i class="fas fa-user-plus"></i> Регистрация</h5>
                    </div>
                    <div class="card-body">
                        <form method="post">
                            <div class="mb-2">
                                <input type="email" name="email" class="form-control" placeholder="📧 Email" required>
                            </div>
                            <div class="mb-2">
                                <input type="text" name="username" class="form-control" placeholder="👤 Имя пользователя" required>
                            </div>
                            <div class="mb-2">
                                <input type="text" name="full_name" class="form-control" placeholder="📛 Полное имя">
                            </div>
                            <div class="mb-2">
                                <input type="password" name="password" class="form-control" placeholder="🔒 Пароль" required>
                            </div>
                            <button type="submit" class="btn btn-primary w-100"><i class="fas fa-check"></i> Зарегистрироваться</button>
                        </form>
                        <hr>
                        <p class="text-center small">Уже есть аккаунт? <a href="/login">Войти</a></p>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

LOGIN_PAGE = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Вход</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    {BASE_STYLE}
</head>
<body class="bg-light">
    <div class="container mt-4">
        <div class="row justify-content-center">
            <div class="col-12 col-sm-10 col-md-6 col-lg-5">
                <div class="card card-shadow fade-in">
                    <div class="card-header bg-success text-white text-center">
                        <h5 class="mb-0"><i class="fas fa-sign-in-alt"></i> Вход</h5>
                    </div>
                    <div class="card-body">
                        <form method="post">
                            <div class="mb-2">
                                <input type="text" name="username" class="form-control" placeholder="👤 Имя пользователя" required>
                            </div>
                            <div class="mb-2">
                                <input type="password" name="password" class="form-control" placeholder="🔒 Пароль" required>
                            </div>
                            <button type="submit" class="btn btn-success w-100"><i class="fas fa-arrow-right"></i> Войти</button>
                        </form>
                        <hr>
                        <p class="text-center small"><a href="/forgot-password">Забыли пароль?</a></p>
                        <p class="text-center small">Нет аккаунта? <a href="/register">Зарегистрироваться</a></p>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

# ==================== МАРШРУТЫ ====================

@app.get("/")
async def home():
    return RedirectResponse("/login")

@app.get("/register")
async def register_page():
    return HTMLResponse(content=REGISTER_PAGE)

@app.post("/register")
async def register(email: str = Form(...), username: str = Form(...), password: str = Form(...), full_name: str = Form(""), db: Session = Depends(get_db)):
    existing = db.query(User).filter((User.email == email) | (User.username == username)).first()
    if existing:
        return HTMLResponse("<div class='container mt-4'><div class='alert alert-danger'><h4>Пользователь уже существует!</h4><a href='/register'>Назад</a></div></div>")
    new_user = User(email=email, username=username, full_name=full_name, hashed_password=hash_password(password))
    db.add(new_user)
    db.commit()
    return RedirectResponse(url="/login", status_code=303)

@app.get("/login")
async def login_page():
    return HTMLResponse(content=LOGIN_PAGE)

@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return HTMLResponse("<div class='container mt-4'><div class='alert alert-danger'><h4>Неверный логин или пароль!</h4><a href='/login'>Назад</a></div></div>")
    token = create_access_token(data={"sub": user.username})
    response = RedirectResponse("/projects", status_code=303)
    response.set_cookie(key="access_token", value=token, httponly=True)
    return response

# ==================== ПРОЕКТЫ ====================

@app.get("/projects")
async def projects_list(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    
    admin_link = '<li class="nav-item"><a class="nav-link" href="/admin"><i class="fas fa-crown"></i> Админ</a></li>' if is_admin(user) else ''
    
    projects = db.query(Project).filter(Project.owner_id == user.id).all()
    
    projects_html = ""
    for p in projects:
        projects_html += f"""
        <div class="col-12 mb-2">
            <div class="card card-shadow fade-in">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start">
                        <h6 class="mb-0"><i class="fas fa-project-diagram text-primary"></i> {p.name}</h6>
                        <span class="badge bg-success">Активный</span>
                    </div>
                    <p class="text-muted small mt-1 mb-2">{p.description[:100] if p.description else "Нет описания"}</p>
                    <a href="/projects/{p.id}/tasks" class="btn btn-primary w-100 btn-sm"><i class="fas fa-tasks"></i> Задачи</a>
                </div>
            </div>
        </div>
        """
    
    if not projects_html:
        projects_html = '<div class="col-12"><div class="alert alert-info text-center">У вас пока нет проектов</div></div>'
    
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Мои проекты</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        {BASE_STYLE}
    </head>
    <body>
        <nav class="navbar navbar-expand-lg navbar-dark bg-dark sticky-top">
            <div class="container">
                <a class="navbar-brand" href="/projects"><i class="fas fa-tasks"></i> ProjectManager</a>
                <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                    <span class="navbar-toggler-icon"></span>
                </button>
                <div class="collapse navbar-collapse" id="navbarNav">
                    <ul class="navbar-nav ms-auto">
                        <li class="nav-item"><a class="nav-link active" href="/projects"><i class="fas fa-folder"></i> Проекты</a></li>
                        <li class="nav-item"><a class="nav-link" href="/tasks"><i class="fas fa-check-square"></i> Задачи</a></li>
                        <li class="nav-item"><a class="nav-link" href="/profile"><i class="fas fa-user"></i> Профиль</a></li>
                        {admin_link}
                        <li class="nav-item"><a class="nav-link" href="/logout"><i class="fas fa-sign-out-alt"></i> Выйти</a></li>
                    </ul>
                </div>
            </div>
        </nav>
        <div class="container mt-3">
            <div class="row">
                <div class="col-12 mb-3">
                    <div class="card card-shadow">
                        <div class="card-header bg-success text-white">
                            <h6 class="mb-0"><i class="fas fa-plus"></i> Создать проект</h6>
                        </div>
                        <div class="card-body">
                            <form method="post" action="/projects/create">
                                <div class="mb-2">
                                    <input type="text" name="name" class="form-control" placeholder="Название" required>
                                </div>
                                <div class="mb-2">
                                    <textarea name="description" class="form-control" rows="2" placeholder="Описание"></textarea>
                                </div>
                                <div class="mb-2">
                                    <select name="status" class="form-select">
                                        <option value="active">Активный</option>
                                        <option value="completed">Завершен</option>
                                        <option value="archived">Архив</option>
                                    </select>
                                </div>
                                <button type="submit" class="btn btn-success w-100"><i class="fas fa-save"></i> Создать</button>
                            </form>
                        </div>
                    </div>
                </div>
                <div class="col-12">
                    <div class="card card-shadow">
                        <div class="card-header bg-primary text-white">
                            <h6 class="mb-0"><i class="fas fa-folder-open"></i> Мои проекты</h6>
                        </div>
                        <div class="card-body">
                            <div class="row project-grid">
                                {projects_html}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """)

@app.post("/projects/create")
async def create_project(request: Request, name: str = Form(...), description: str = Form(""), status: str = Form("active"), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    new_project = Project(name=name, description=description, status=status, owner_id=user.id)
    db.add(new_project)
    db.commit()
    return RedirectResponse("/projects", status_code=303)

# ==================== ЗАДАЧИ ====================

@app.get("/tasks")
async def tasks_list(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    
    admin_link = '<li class="nav-item"><a class="nav-link" href="/admin"><i class="fas fa-crown"></i> Админ</a></li>' if is_admin(user) else ''
    
    tasks = db.query(Task).filter(Task.created_by == user.id).order_by(desc(Task.created_at)).all()
    
    projects = db.query(Project).filter(Project.owner_id == user.id).all()
    projects_options = ""
    for p in projects:
        projects_options += f'<option value="{p.id}">{p.name}</option>'
    
    tasks_html = ""
    for t in tasks:
        status_badge = "secondary" if t.status == "todo" else "primary" if t.status == "in_progress" else "warning" if t.status == "review" else "success"
        status_text = "To Do" if t.status == "todo" else "В работе" if t.status == "in_progress" else "На проверке" if t.status == "review" else "Выполнено"
        tasks_html += f"""
        <div class="col-12 mb-2">
            <div class="card card-shadow task-card fade-in">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start">
                        <h6 class="mb-0"><a href="/tasks/{t.id}" class="text-decoration-none">{t.title}</a></h6>
                        <span class="badge bg-{status_badge}">{status_text}</span>
                    </div>
                    <p class="text-muted small mt-1 mb-1">{t.description[:80] if t.description else "Нет описания"}</p>
                    <small class="text-muted">Приоритет: {t.priority}</small>
                </div>
            </div>
        </div>
        """
    
    if not tasks_html:
        tasks_html = '<div class="col-12"><div class="alert alert-info text-center">Нет задач</div></div>'
    
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Мои задачи</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        {BASE_STYLE}
    </head>
    <body>
        <nav class="navbar navbar-expand-lg navbar-dark bg-dark sticky-top">
            <div class="container">
                <a class="navbar-brand" href="/projects"><i class="fas fa-tasks"></i> ProjectManager</a>
                <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                    <span class="navbar-toggler-icon"></span>
                </button>
                <div class="collapse navbar-collapse" id="navbarNav">
                    <ul class="navbar-nav ms-auto">
                        <li class="nav-item"><a class="nav-link" href="/projects"><i class="fas fa-folder"></i> Проекты</a></li>
                        <li class="nav-item"><a class="nav-link active" href="/tasks"><i class="fas fa-check-square"></i> Задачи</a></li>
                        <li class="nav-item"><a class="nav-link" href="/profile"><i class="fas fa-user"></i> Профиль</a></li>
                        {admin_link}
                        <li class="nav-item"><a class="nav-link" href="/logout"><i class="fas fa-sign-out-alt"></i> Выйти</a></li>
                    </ul>
                </div>
            </div>
        </nav>
        <div class="container mt-3">
            <div class="row">
                <div class="col-12 mb-3">
                    <div class="card card-shadow">
                        <div class="card-header bg-success text-white">
                            <h6 class="mb-0"><i class="fas fa-plus"></i> Создать задачу</h6>
                        </div>
                        <div class="card-body">
                            <form method="post" action="/tasks/create">
                                <div class="mb-2">
                                    <input type="text" name="title" class="form-control" placeholder="Название" required>
                                </div>
                                <div class="mb-2">
                                    <textarea name="description" class="form-control" rows="2" placeholder="Описание"></textarea>
                                </div>
                                <div class="mb-2">
                                    <select name="project_id" class="form-select" required>
                                        <option value="">Выберите проект</option>
                                        {projects_options}
                                    </select>
                                </div>
                                <div class="row g-1">
                                    <div class="col-6">
                                        <select name="status" class="form-select">
                                            <option value="todo">To Do</option>
                                            <option value="in_progress">В работе</option>
                                            <option value="review">На проверке</option>
                                            <option value="done">Выполнено</option>
                                        </select>
                                    </div>
                                    <div class="col-6">
                                        <select name="priority" class="form-select">
                                            <option value="low">Низкий</option>
                                            <option value="medium" selected>Средний</option>
                                            <option value="high">Высокий</option>
                                            <option value="urgent">Срочный</option>
                                        </select>
                                    </div>
                                </div>
                                <button type="submit" class="btn btn-success w-100 mt-2"><i class="fas fa-save"></i> Создать</button>
                            </form>
                        </div>
                    </div>
                </div>
                <div class="col-12">
                    <div class="card card-shadow">
                        <div class="card-header bg-primary text-white">
                            <h6 class="mb-0"><i class="fas fa-list"></i> Мои задачи</h6>
                        </div>
                        <div class="card-body">
                            <div class="row task-grid">
                                {tasks_html}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """)

@app.post("/tasks/create")
async def create_task(request: Request, title: str = Form(...), description: str = Form(""), status: str = Form("todo"), priority: str = Form("medium"), project_id: int = Form(...), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    
    new_task = Task(
        title=title,
        description=description,
        status=status,
        priority=priority,
        project_id=project_id,
        created_by=user.id
    )
    db.add(new_task)
    db.commit()
    return RedirectResponse("/tasks", status_code=303)

# ==================== ОСТАЛЬНЫЕ МАРШРУТЫ ====================

@app.get("/tasks/{task_id}")
async def task_detail(task_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return HTMLResponse("<div class='container mt-4'><div class='alert alert-danger'>Задача не найдена</div></div>")
    
    comments = db.query(Comment).filter(Comment.task_id == task_id).order_by(desc(Comment.created_at)).all()
    comments_html = ""
    for c in comments:
        comment_user = db.query(User).filter(User.id == c.user_id).first()
        username = comment_user.username if comment_user else "Unknown"
        comments_html += f"""
        <div class="border-bottom p-2">
            <strong>{username}</strong> <small class="text-muted">{c.created_at}</small>
            <p>{c.content}</p>
        </div>
        """
    
    if not comments_html:
        comments_html = '<p class="text-muted">Нет комментариев</p>'
    
    status_names = {"todo": "To Do", "in_progress": "В работе", "review": "На проверке", "done": "Выполнено"}
    priority_names = {"low": "Низкий", "medium": "Средний", "high": "Высокий", "urgent": "Срочный"}
    
    creator = db.query(User).filter(User.id == task.created_by).first()
    assignee = db.query(User).filter(User.id == task.assigned_to).first() if task.assigned_to else None
    project = db.query(Project).filter(Project.id == task.project_id).first()
    
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{task.title}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        {BASE_STYLE}
    </head>
    <body>
        <nav class="navbar navbar-dark bg-dark sticky-top">
            <div class="container">
                <a class="navbar-brand" href="/projects"><i class="fas fa-tasks"></i> ProjectManager</a>
                <div class="navbar-nav ms-auto">
                    <a class="nav-link" href="/tasks"><i class="fas fa-arrow-left"></i> Назад</a>
                    <a class="nav-link" href="/logout"><i class="fas fa-sign-out-alt"></i> Выйти</a>
                </div>
            </div>
        </nav>
        <div class="container mt-3">
            <div class="row">
                <div class="col-12">
                    <div class="card card-shadow">
                        <div class="card-header bg-primary text-white">
                            <h6 class="mb-0">{task.title}</h6>
                        </div>
                        <div class="card-body">
                            <p><strong>Описание:</strong> {task.description or "Нет описания"}</p>
                            <p><strong>Статус:</strong> <span class="badge bg-secondary">{status_names.get(task.status, task.status)}</span></p>
                            <p><strong>Приоритет:</strong> {priority_names.get(task.priority, task.priority)}</p>
                            <p><strong>Проект:</strong> {project.name if project else "Без проекта"}</p>
                            <p><strong>Создал:</strong> {creator.username if creator else "Unknown"}</p>
                            <div class="d-flex gap-2 mt-3">
                                <a href="/tasks/{task.id}/edit" class="btn btn-warning flex-fill"><i class="fas fa-edit"></i> Редактировать</a>
                                <a href="/tasks/{task.id}/delete" class="btn btn-danger flex-fill" onclick="return confirm('Удалить?')"><i class="fas fa-trash"></i> Удалить</a>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-12 mt-3">
                    <div class="card card-shadow">
                        <div class="card-header bg-secondary text-white">
                            <h6 class="mb-0"><i class="fas fa-comments"></i> Комментарии ({len(comments)})</h6>
                        </div>
                        <div class="card-body">
                            {comments_html}
                            <hr>
                            <form method="post" action="/tasks/{task.id}/comment">
                                <div class="d-flex gap-2">
                                    <input type="text" name="content" class="form-control" placeholder="Написать комментарий..." required>
                                    <button type="submit" class="btn btn-primary"><i class="fas fa-paper-plane"></i></button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """)

@app.post("/tasks/{task_id}/comment")
async def add_comment(task_id: int, request: Request, content: str = Form(...), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    
    new_comment = Comment(content=content, task_id=task_id, user_id=user.id)
    db.add(new_comment)
    db.commit()
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if task and task.created_by != user.id:
        add_notification(
            user_id=task.created_by,
            title="Новый комментарий",
            message=f"{user.username} оставил комментарий к задаче '{task.title}'",
            type="info",
            link=f"/tasks/{task_id}",
            db=db
        )
    return RedirectResponse(f"/tasks/{task_id}", status_code=303)

@app.get("/tasks/{task_id}/edit")
async def edit_task_page(task_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    
    task = db.query(Task).filter(Task.id == task_id, Task.created_by == user.id).first()
    if not task:
        return HTMLResponse("<div class='container mt-4'><div class='alert alert-danger'>Задача не найдена</div></div>")
    
    projects = db.query(Project).filter(Project.owner_id == user.id).all()
    projects_options = ""
    for p in projects:
        selected = "selected" if p.id == task.project_id else ""
        projects_options += f'<option value="{p.id}" {selected}>{p.name}</option>'
    
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Редактирование задачи</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        {BASE_STYLE}
    </head>
    <body class="bg-light">
        <nav class="navbar navbar-expand-lg navbar-dark bg-dark sticky-top">
            <div class="container">
                <a class="navbar-brand" href="/projects"><i class="fas fa-tasks"></i> ProjectManager</a>
                <div class="navbar-nav ms-auto">
                    <a class="nav-link" href="/tasks"><i class="fas fa-arrow-left"></i> Назад</a>
                    <a class="nav-link" href="/logout"><i class="fas fa-sign-out-alt"></i> Выйти</a>
                </div>
            </div>
        </nav>
        <div class="container mt-3">
            <div class="row justify-content-center">
                <div class="col-12 col-md-8 col-lg-6">
                    <div class="card card-shadow">
                        <div class="card-header bg-warning text-dark">
                            <h6 class="mb-0"><i class="fas fa-edit"></i> Редактирование задачи</h6>
                        </div>
                        <div class="card-body">
                            <form method="post" action="/tasks/{task_id}/edit">
                                <div class="mb-2">
                                    <input type="text" name="title" class="form-control" value="{task.title}" placeholder="Название" required>
                                </div>
                                <div class="mb-2">
                                    <textarea name="description" class="form-control" rows="3">{task.description or ""}</textarea>
                                </div>
                                <div class="row g-2">
                                    <div class="col-6">
                                        <select name="status" class="form-select">
                                            <option value="todo" {'selected' if task.status == 'todo' else ''}>To Do</option>
                                            <option value="in_progress" {'selected' if task.status == 'in_progress' else ''}>В работе</option>
                                            <option value="review" {'selected' if task.status == 'review' else ''}>На проверке</option>
                                            <option value="done" {'selected' if task.status == 'done' else ''}>Выполнено</option>
                                        </select>
                                    </div>
                                    <div class="col-6">
                                        <select name="priority" class="form-select">
                                            <option value="low" {'selected' if task.priority == 'low' else ''}>Низкий</option>
                                            <option value="medium" {'selected' if task.priority == 'medium' else ''}>Средний</option>
                                            <option value="high" {'selected' if task.priority == 'high' else ''}>Высокий</option>
                                            <option value="urgent" {'selected' if task.priority == 'urgent' else ''}>Срочный</option>
                                        </select>
                                    </div>
                                </div>
                                <div class="mb-2 mt-2">
                                    <select name="project_id" class="form-select" required>
                                        {projects_options}
                                    </select>
                                </div>
                                <div class="d-flex gap-2">
                                    <a href="/tasks" class="btn btn-secondary flex-fill"><i class="fas fa-times"></i> Отмена</a>
                                    <button type="submit" class="btn btn-warning flex-fill"><i class="fas fa-save"></i> Сохранить</button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """)

@app.post("/tasks/{task_id}/edit")
async def edit_task(task_id: int, request: Request, title: str = Form(...), description: str = Form(""), status: str = Form("todo"), priority: str = Form("medium"), project_id: int = Form(...), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    
    task = db.query(Task).filter(Task.id == task_id, Task.created_by == user.id).first()
    if task:
        task.title = title
        task.description = description
        task.status = status
        task.priority = priority
        task.project_id = project_id
        task.updated_at = str(datetime.now())
        db.commit()
    return RedirectResponse("/tasks", status_code=303)

@app.get("/tasks/{task_id}/delete")
async def delete_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    
    task = db.query(Task).filter(Task.id == task_id, Task.created_by == user.id).first()
    if task:
        db.delete(task)
        db.commit()
    return RedirectResponse("/tasks", status_code=303)

@app.get("/tasks/{task_id}/status/{new_status}")
async def update_task_status(task_id: int, new_status: str, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    
    task = db.query(Task).filter(Task.id == task_id, Task.created_by == user.id).first()
    if task:
        task.status = new_status
        task.updated_at = str(datetime.now())
        db.commit()
    return RedirectResponse("/tasks", status_code=303)

@app.get("/projects/{project_id}/tasks")
async def project_tasks(project_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    
    project = db.query(Project).filter(Project.id == project_id, Project.owner_id == user.id).first()
    if not project:
        return RedirectResponse("/projects")
    
    tasks = db.query(Task).filter(Task.project_id == project_id).all()
    
    tasks_html = ""
    if tasks:
        for t in tasks:
            status_color = "secondary" if t.status == "todo" else "primary" if t.status == "in_progress" else "warning" if t.status == "review" else "success"
            status_text = "To Do" if t.status == "todo" else "В работе" if t.status == "in_progress" else "На проверке" if t.status == "review" else "Выполнено"
            tasks_html += f"""
            <div class="col-12 mb-2">
                <div class="card card-shadow">
                    <div class="card-body">
                        <div class="d-flex justify-content-between">
                            <h6 class="mb-0">{t.title}</h6>
                            <span class="badge bg-{status_color}">{status_text}</span>
                        </div>
                        <p class="text-muted small mt-1">{t.description[:100] if t.description else ""}</p>
                        <div class="d-flex gap-1">
                            <a href="/tasks/{t.id}" class="btn btn-sm btn-outline-primary flex-fill"><i class="fas fa-eye"></i></a>
                            <a href="/tasks/{t.id}/edit" class="btn btn-sm btn-outline-warning flex-fill"><i class="fas fa-edit"></i></a>
                            <a href="/tasks/{t.id}/delete" class="btn btn-sm btn-outline-danger flex-fill"><i class="fas fa-trash"></i></a>
                        </div>
                    </div>
                </div>
            </div>
            """
    else:
        tasks_html = '<div class="col-12"><div class="alert alert-info">В этом проекте пока нет задач</div></div>'
    
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Задачи проекта: {project.name}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        {BASE_STYLE}
    </head>
    <body>
        <nav class="navbar navbar-dark bg-dark sticky-top">
            <div class="container">
                <a class="navbar-brand" href="/projects"><i class="fas fa-tasks"></i> ProjectManager</a>
                <div class="navbar-nav ms-auto">
                    <a class="nav-link" href="/projects"><i class="fas fa-arrow-left"></i> Назад</a>
                    <a class="nav-link" href="/logout"><i class="fas fa-sign-out-alt"></i> Выйти</a>
                </div>
            </div>
        </nav>
        <div class="container mt-3">
            <div class="card card-shadow">
                <div class="card-header bg-primary text-white">
                    <h6 class="mb-0"><i class="fas fa-project-diagram"></i> {project.name}</h6>
                </div>
                <div class="card-body">
                    <p class="text-muted small">{project.description or "Описание отсутствует"}</p>
                    <hr>
                    <div class="row">
                        {tasks_html}
                    </div>
                </div>
            </div>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """)

# ==================== ПРОФИЛЬ ====================

@app.get("/profile")
async def profile(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    
    unread_count = db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read == False).count()
    admin_link = '<li class="nav-item"><a class="nav-link" href="/admin"><i class="fas fa-crown"></i> Админ</a></li>' if is_admin(user) else ''
    
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Личный кабинет</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        {BASE_STYLE}
    </head>
    <body>
        <nav class="navbar navbar-expand-lg navbar-dark bg-dark sticky-top">
            <div class="container">
                <a class="navbar-brand" href="/projects"><i class="fas fa-tasks"></i> ProjectManager</a>
                <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                    <span class="navbar-toggler-icon"></span>
                </button>
                <div class="collapse navbar-collapse" id="navbarNav">
                    <ul class="navbar-nav ms-auto">
                        <li class="nav-item"><a class="nav-link" href="/projects"><i class="fas fa-folder"></i> Проекты</a></li>
                        <li class="nav-item"><a class="nav-link" href="/tasks"><i class="fas fa-check-square"></i> Задачи</a></li>
                        <li class="nav-item"><a class="nav-link active" href="/profile"><i class="fas fa-user"></i> Профиль</a></li>
                        <li class="nav-item"><a class="nav-link" href="/notifications"><i class="fas fa-bell"></i> <span class="badge bg-danger">{unread_count}</span></a></li>
                        {admin_link}
                        <li class="nav-item"><a class="nav-link" href="/logout"><i class="fas fa-sign-out-alt"></i> Выйти</a></li>
                    </ul>
                </div>
            </div>
        </nav>
        <div class="container mt-3">
            <div class="row">
                <div class="col-12">
                    <div class="card card-shadow">
                        <div class="card-header bg-info text-white text-center">
                            <h6 class="mb-0"><i class="fas fa-id-card"></i> Личный кабинет</h6>
                        </div>
                        <div class="card-body">
                            <div class="text-center mb-3">
                                <i class="fas fa-user-circle fa-4x text-secondary"></i>
                                <h5 class="mt-2">{user.username}</h5>
                            </div>
                            <div class="table-responsive">
                                <table class="table">
                                    <tr><td><strong>Полное имя:</strong></td><td>{user.full_name or "Не указано"}</td></tr>
                                    <tr><td><strong>Email:</strong></td><td>{user.email}</td></tr>
                                    <tr><td><strong>Роль:</strong></td><td><span class="badge bg-primary">{user.role}</span></td></tr>
                                    <tr><td><strong>Дата регистрации:</strong></td><td>{user.created_at}</td></tr>
                                </table>
                            </div>
                            <div class="d-grid gap-2">
                                <a href="/profile/edit" class="btn btn-warning"><i class="fas fa-edit"></i> Редактировать</a>
                                <a href="/profile/change-password" class="btn btn-danger"><i class="fas fa-key"></i> Сменить пароль</a>
                                <a href="/notifications" class="btn btn-info"><i class="fas fa-bell"></i> Уведомления ({unread_count})</a>
                                <a href="/activity" class="btn btn-secondary"><i class="fas fa-history"></i> Моя активность</a>
                                {'<a href="/admin" class="btn btn-danger"><i class="fas fa-crown"></i> Админ-панель</a>' if is_admin(user) else ''}
                                <a href="/projects" class="btn btn-primary"><i class="fas fa-arrow-left"></i> Назад</a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """)

@app.get("/profile/edit")
async def edit_profile_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Редактирование профиля</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        {BASE_STYLE}
    </head>
    <body class="bg-light">
        <div class="container mt-3">
            <div class="row justify-content-center">
                <div class="col-12 col-md-6 col-lg-5">
                    <div class="card card-shadow">
                        <div class="card-header bg-warning text-dark">
                            <h6 class="mb-0"><i class="fas fa-edit"></i> Редактирование</h6>
                        </div>
                        <div class="card-body">
                            <form method="post" action="/profile/edit">
                                <div class="mb-2">
                                    <input type="email" name="email" class="form-control" value="{user.email}" required>
                                </div>
                                <div class="mb-2">
                                    <input type="text" name="username" class="form-control" value="{user.username}" required>
                                </div>
                                <div class="mb-2">
                                    <input type="text" name="full_name" class="form-control" value="{user.full_name or ''}" placeholder="Полное имя">
                                </div>
                                <button type="submit" class="btn btn-warning w-100"><i class="fas fa-save"></i> Сохранить</button>
                                <a href="/profile" class="btn btn-secondary w-100 mt-2"><i class="fas fa-times"></i> Отмена</a>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """)

@app.post("/profile/edit")
async def edit_profile(request: Request, email: str = Form(...), username: str = Form(...), full_name: str = Form(""), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    user.email = email
    user.username = username
    user.full_name = full_name
    db.commit()
    return RedirectResponse("/profile", status_code=303)

@app.get("/profile/change-password")
async def change_password_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Смена пароля</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        {BASE_STYLE}
    </head>
    <body class="bg-light">
        <div class="container mt-3">
            <div class="row justify-content-center">
                <div class="col-12 col-md-6 col-lg-5">
                    <div class="card card-shadow">
                        <div class="card-header bg-danger text-white">
                            <h6 class="mb-0"><i class="fas fa-key"></i> Смена пароля</h6>
                        </div>
                        <div class="card-body">
                            <form method="post" action="/profile/change-password">
                                <div class="mb-2">
                                    <input type="password" name="old_password" class="form-control" placeholder="Текущий пароль" required>
                                </div>
                                <div class="mb-2">
                                    <input type="password" name="new_password" class="form-control" placeholder="Новый пароль" required>
                                </div>
                                <div class="mb-2">
                                    <input type="password" name="confirm_password" class="form-control" placeholder="Подтверждение" required>
                                </div>
                                <button type="submit" class="btn btn-danger w-100"><i class="fas fa-save"></i> Сменить</button>
                                <a href="/profile" class="btn btn-secondary w-100 mt-2"><i class="fas fa-times"></i> Отмена</a>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """)

@app.post("/profile/change-password")
async def change_password(request: Request, old_password: str = Form(...), new_password: str = Form(...), confirm_password: str = Form(...), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    if new_password != confirm_password:
        return HTMLResponse("<div class='container mt-4'><div class='alert alert-danger'>Пароли не совпадают</div></div>")
    if not verify_password(old_password, user.hashed_password):
        return HTMLResponse("<div class='container mt-4'><div class='alert alert-danger'>Неверный текущий пароль</div></div>")
    user.hashed_password = hash_password(new_password)
    db.commit()
    return HTMLResponse("<div class='container mt-4'><div class='alert alert-success'>Пароль изменен! <a href='/profile'>В профиль</a></div></div>")

@app.get("/forgot-password")
async def forgot_password_page():
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Восстановление пароля</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        {BASE_STYLE}
    </head>
    <body class="bg-light">
        <div class="container mt-3">
            <div class="row justify-content-center">
                <div class="col-12 col-md-6 col-lg-5">
                    <div class="card card-shadow">
                        <div class="card-header bg-warning text-dark">
                            <h6 class="mb-0"><i class="fas fa-key"></i> Восстановление</h6>
                        </div>
                        <div class="card-body">
                            <form method="post" action="/forgot-password">
                                <div class="mb-2">
                                    <input type="email" name="email" class="form-control" placeholder="Email" required>
                                </div>
                                <button type="submit" class="btn btn-warning w-100"><i class="fas fa-paper-plane"></i> Отправить</button>
                                <a href="/login" class="btn btn-secondary w-100 mt-2"><i class="fas fa-arrow-left"></i> Назад</a>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """)

@app.post("/forgot-password")
async def forgot_password(email: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if user:
        token = generate_reset_token()
        user.reset_token = token
        user.reset_token_expires = str(datetime.now() + timedelta(hours=1))
        db.commit()
        return HTMLResponse(f"""
        <div class='container mt-4'>
            <div class='alert alert-success'>
                <h5>Ссылка для сброса</h5>
                <a href='/reset-password?token={token}'>Сбросить пароль</a>
            </div>
        </div>
        """)
    return HTMLResponse("<div class='container mt-4'><div class='alert alert-danger'>Email не найден</div></div>")

@app.get("/reset-password")
async def reset_password_page(token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.reset_token == token).first()
    if not user:
        return HTMLResponse("<div class='container mt-4'><div class='alert alert-danger'>Неверная ссылка</div></div>")
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Сброс пароля</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        {BASE_STYLE}
    </head>
    <body class="bg-light">
        <div class="container mt-3">
            <div class="row justify-content-center">
                <div class="col-12 col-md-6 col-lg-5">
                    <div class="card card-shadow">
                        <div class="card-header bg-info text-white">
                            <h6 class="mb-0"><i class="fas fa-lock"></i> Новый пароль</h6>
                        </div>
                        <div class="card-body">
                            <form method="post" action="/reset-password">
                                <input type="hidden" name="token" value="{token}">
                                <div class="mb-2">
                                    <input type="password" name="new_password" class="form-control" placeholder="Новый пароль" required>
                                </div>
                                <div class="mb-2">
                                    <input type="password" name="confirm_password" class="form-control" placeholder="Подтверждение" required>
                                </div>
                                <button type="submit" class="btn btn-info w-100"><i class="fas fa-save"></i> Сохранить</button>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """)

@app.post("/reset-password")
async def reset_password(token: str = Form(...), new_password: str = Form(...), confirm_password: str = Form(...), db: Session = Depends(get_db)):
    if new_password != confirm_password:
        return HTMLResponse("<div class='container mt-4'><div class='alert alert-danger'>Пароли не совпадают</div></div>")
    user = db.query(User).filter(User.reset_token == token).first()
    if not user:
        return HTMLResponse("<div class='container mt-4'><div class='alert alert-danger'>Неверная ссылка</div></div>")
    user.hashed_password = hash_password(new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()
    return HTMLResponse("<div class='container mt-4'><div class='alert alert-success'>Пароль изменен! <a href='/login'>Войти</a></div></div>")

# ==================== УВЕДОМЛЕНИЯ ====================

@app.get("/notifications")
async def notifications_list(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    
    notifications = db.query(Notification).filter(Notification.user_id == user.id).order_by(desc(Notification.created_at)).all()
    
    notifications_html = ""
    for n in notifications:
        is_read = "✅" if n.is_read else "🔴"
        type_color = {"info": "primary", "success": "success", "warning": "warning", "danger": "danger"}.get(n.type, "primary")
        notifications_html += f"""
        <div class="card mb-2 border-{type_color} card-shadow">
            <div class="card-body">
                <div class="d-flex justify-content-between">
                    <h6 class="mb-0">{n.title} {is_read}</h6>
                    <small class="text-muted">{n.created_at}</small>
                </div>
                <p class="small mt-1">{n.message}</p>
                <div class="d-flex gap-2">
                    <a href="/notifications/{n.id}/read" class="btn btn-sm btn-outline-primary flex-fill"><i class="fas fa-check"></i> Прочитано</a>
                    {f'<a href="{n.link}" class="btn btn-sm btn-outline-secondary flex-fill"><i class="fas fa-link"></i> Перейти</a>' if n.link else ''}
                </div>
            </div>
        </div>
        """
    
    if not notifications_html:
        notifications_html = '<div class="alert alert-info text-center">У вас нет уведомлений 🎉</div>'
    
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Уведомления</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        {BASE_STYLE}
    </head>
    <body>
        <nav class="navbar navbar-dark bg-dark sticky-top">
            <div class="container">
                <a class="navbar-brand" href="/projects"><i class="fas fa-tasks"></i> ProjectManager</a>
                <div class="navbar-nav ms-auto">
                    <a class="nav-link" href="/profile"><i class="fas fa-user"></i> Профиль</a>
                    <a class="nav-link" href="/logout"><i class="fas fa-sign-out-alt"></i> Выйти</a>
                </div>
            </div>
        </nav>
        <div class="container mt-3">
            <div class="d-flex justify-content-between align-items-center">
                <h5 class="mb-0"><i class="fas fa-bell"></i> Уведомления</h5>
                <a href="/notifications/mark-all-read" class="btn btn-secondary btn-sm"><i class="fas fa-check-double"></i> Все</a>
            </div>
            <hr>
            {notifications_html}
        </div>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """)

@app.get("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    notification = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == user.id).first()
    if notification:
        notification.is_read = True
        db.commit()
    return RedirectResponse("/notifications", status_code=303)

@app.get("/notifications/mark-all-read")
async def mark_all_notifications_read(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read == False).update({"is_read": True})
    db.commit()
    return RedirectResponse("/notifications", status_code=303)

@app.get("/activity")
async def activity_list(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    
    activities = db.query(ActivityLog).filter(ActivityLog.user_id == user.id).order_by(desc(ActivityLog.created_at)).limit(50).all()
    
    activity_html = ""
    for a in activities:
        activity_html += f"""
        <div class="border-bottom p-2">
            <strong>{a.action}</strong>
            <p class="small">{a.details}</p>
            <small class="text-muted">{a.created_at}</small>
        </div>
        """
    
    if not activity_html:
        activity_html = '<div class="alert alert-info text-center">Нет активности</div>'
    
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Моя активность</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        {BASE_STYLE}
    </head>
    <body>
        <nav class="navbar navbar-dark bg-dark sticky-top">
            <div class="container">
                <a class="navbar-brand" href="/projects"><i class="fas fa-tasks"></i> ProjectManager</a>
                <div class="navbar-nav ms-auto">
                    <a class="nav-link" href="/profile"><i class="fas fa-user"></i> Профиль</a>
                    <a class="nav-link" href="/logout"><i class="fas fa-sign-out-alt"></i> Выйти</a>
                </div>
            </div>
        </nav>
        <div class="container mt-3">
            <h5><i class="fas fa-history"></i> Моя активность</h5>
            <hr>
            <div class="card card-shadow">
                <div class="card-body" style="max-height:500px; overflow-y:auto;">
                    {activity_html}
                </div>
            </div>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """)

# ==================== АДМИН-ПАНЕЛЬ ====================

@app.get("/admin")
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or not is_admin(user):
        return HTMLResponse("""
        <div class='container mt-4'>
            <div class='alert alert-danger'><h4>403 Доступ запрещен</h4></div>
        </div>
        """)
    
    total_users = db.query(User).count()
    total_projects = db.query(Project).count()
    total_tasks = db.query(Task).count()
    total_comments = db.query(Comment).count()
    
    activities = db.query(ActivityLog).order_by(desc(ActivityLog.created_at)).limit(10).all()
    activity_html = ""
    if activities:
        for a in activities:
            user_obj = db.query(User).filter(User.id == a.user_id).first()
            username = user_obj.username if user_obj else "Unknown"
            activity_html += f"""
            <div class="border-bottom p-2">
                <strong>{username}</strong> - {a.action}
                <p class="text-muted small mb-0">{a.details}</p>
                <small class="text-muted">{a.created_at}</small>
            </div>
            """
    else:
        activity_html = '<p class="text-muted text-center my-3">Нет активности</p>'
    
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Админ-панель</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        {BASE_STYLE}
    </head>
    <body class="bg-light">
        <nav class="navbar navbar-expand-lg navbar-dark bg-dark sticky-top">
            <div class="container">
                <a class="navbar-brand" href="/admin"><i class="fas fa-crown"></i> Админ-панель</a>
                <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                    <span class="navbar-toggler-icon"></span>
                </button>
                <div class="collapse navbar-collapse" id="navbarNav">
                    <ul class="navbar-nav ms-auto">
                        <li class="nav-item"><a class="nav-link active" href="/admin"><i class="fas fa-dashboard"></i> Дашборд</a></li>
                        <li class="nav-item"><a class="nav-link" href="/admin/users"><i class="fas fa-users"></i> Пользователи</a></li>
                        <li class="nav-item"><a class="nav-link" href="/admin/projects"><i class="fas fa-folder"></i> Проекты</a></li>
                        <li class="nav-item"><a class="nav-link" href="/projects"><i class="fas fa-arrow-left"></i> На сайт</a></li>
                        <li class="nav-item"><a class="nav-link" href="/logout"><i class="fas fa-sign-out-alt"></i> Выйти</a></li>
                    </ul>
                </div>
            </div>
        </nav>
        <div class="container mt-4">
            <h4><i class="fas fa-dashboard text-primary"></i> Панель управления</h4>
            <p class="text-muted">Добро пожаловать, <strong>{user.username}</strong>!</p>
            
            <div class="row stat-cards mt-3">
                <div class="col-6 col-md-3 mb-3">
                    <div class="card stat-card text-white bg-primary">
                        <div class="card-body text-center">
                            <h5><i class="fas fa-users"></i></h5>
                            <h2>{total_users}</h2>
                            <p>Пользователи</p>
                        </div>
                    </div>
                </div>
                <div class="col-6 col-md-3 mb-3">
                    <div class="card stat-card text-white bg-success">
                        <div class="card-body text-center">
                            <h5><i class="fas fa-folder"></i></h5>
                            <h2>{total_projects}</h2>
                            <p>Проекты</p>
                        </div>
                    </div>
                </div>
                <div class="col-6 col-md-3 mb-3">
                    <div class="card stat-card text-white bg-warning">
                        <div class="card-body text-center">
                            <h5><i class="fas fa-tasks"></i></h5>
                            <h2>{total_tasks}</h2>
                            <p>Задачи</p>
                        </div>
                    </div>
                </div>
                <div class="col-6 col-md-3 mb-3">
                    <div class="card stat-card text-white bg-info">
                        <div class="card-body text-center">
                            <h5><i class="fas fa-comments"></i></h5>
                            <h2>{total_comments}</h2>
                            <p>Комментарии</p>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="card shadow mt-3">
                <div class="card-header bg-dark text-white">
                    <h6 class="mb-0"><i class="fas fa-clock"></i> Последняя активность</h6>
                </div>
                <div class="card-body" style="max-height: 400px; overflow-y: auto;">
                    {activity_html}
                </div>
            </div>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """)

@app.get("/admin/users")
async def admin_users(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or not is_admin(user):
        return HTMLResponse("<div class='container mt-4'><div class='alert alert-danger'><h4>403 Доступ запрещен</h4></div></div>")
    
    users = db.query(User).all()
    users_html = ""
    for u in users:
        role_badge = "bg-primary" if u.role == "admin" else "bg-secondary"
        active_badge = "bg-success" if u.is_active else "bg-danger"
        users_html += f"""
        <tr>
            <td>{u.id}</td>
            <td>{u.username}</td>
            <td>{u.email}</td>
            <td><span class="badge {role_badge}">{u.role}</span></td>
            <td><span class="badge {active_badge}">{'Да' if u.is_active else 'Нет'}</span></td>
            <td>
                <div class="d-flex gap-1">
                    <form method="post" action="/admin/users/{u.id}/toggle" style="display:inline">
                        <button class="btn btn-sm btn-outline-warning"><i class="fas fa-toggle-{'on' if u.is_active else 'off'}"></i></button>
                    </form>
                    <form method="post" action="/admin/users/{u.id}/make-admin" style="display:inline">
                        <button class="btn btn-sm btn-outline-primary"><i class="fas fa-crown"></i></button>
                    </form>
                </div>
            </td>
        </tr>
        """
    
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Управление пользователями</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        {BASE_STYLE}
    </head>
    <body class="bg-light">
        <nav class="navbar navbar-expand-lg navbar-dark bg-dark sticky-top">
            <div class="container">
                <a class="navbar-brand" href="/admin"><i class="fas fa-crown"></i> Админ</a>
                <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                    <span class="navbar-toggler-icon"></span>
                </button>
                <div class="collapse navbar-collapse" id="navbarNav">
                    <ul class="navbar-nav ms-auto">
                        <li class="nav-item"><a class="nav-link" href="/admin"><i class="fas fa-dashboard"></i> Дашборд</a></li>
                        <li class="nav-item"><a class="nav-link active" href="/admin/users"><i class="fas fa-users"></i> Пользователи</a></li>
                        <li class="nav-item"><a class="nav-link" href="/admin/projects"><i class="fas fa-folder"></i> Проекты</a></li>
                        <li class="nav-item"><a class="nav-link" href="/projects"><i class="fas fa-arrow-left"></i> На сайт</a></li>
                        <li class="nav-item"><a class="nav-link" href="/logout"><i class="fas fa-sign-out-alt"></i> Выйти</a></li>
                    </ul>
                </div>
            </div>
        </nav>
        <div class="container mt-3">
            <h5><i class="fas fa-users text-primary"></i> Пользователи</h5>
            <hr>
            <div class="card shadow">
                <div class="card-body table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Имя</th>
                                <th>Email</th>
                                <th>Роль</th>
                                <th>Активен</th>
                                <th>Действия</th>
                            </tr>
                        </thead>
                        <tbody>
                            {users_html}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """)

@app.post("/admin/users/{user_id}/toggle")
async def admin_toggle_user(user_id: int, request: Request, db: Session = Depends(get_db)):
    admin_user = get_current_user(request, db)
    if not admin_user or not is_admin(admin_user):
        return HTMLResponse("<div class='container mt-4'><div class='alert alert-danger'>403 Доступ запрещен</div></div>")
    target_user = db.query(User).filter(User.id == user_id).first()
    if target_user:
        target_user.is_active = not target_user.is_active
        db.commit()
    return RedirectResponse("/admin/users", status_code=303)

@app.post("/admin/users/{user_id}/make-admin")
async def admin_make_admin(user_id: int, request: Request, db: Session = Depends(get_db)):
    admin_user = get_current_user(request, db)
    if not admin_user or not is_admin(admin_user):
        return HTMLResponse("<div class='container mt-4'><div class='alert alert-danger'>403 Доступ запрещен</div></div>")
    target_user = db.query(User).filter(User.id == user_id).first()
    if target_user:
        target_user.role = "admin"
        db.commit()
    return RedirectResponse("/admin/users", status_code=303)

@app.get("/admin/projects")
async def admin_projects(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or not is_admin(user):
        return HTMLResponse("<div class='container mt-4'><div class='alert alert-danger'>403 Доступ запрещен</div></div>")
    
    projects = db.query(Project).all()
    projects_html = ""
    for p in projects:
        owner = db.query(User).filter(User.id == p.owner_id).first()
        owner_name = owner.username if owner else "Unknown"
        tasks_count = db.query(Task).filter(Task.project_id == p.id).count()
        status_badge = "bg-success" if p.status == "active" else "bg-secondary" if p.status == "completed" else "bg-danger"
        projects_html += f"""
        <tr>
            <td>{p.id}</td>
            <td>{p.name}</td>
            <td>{owner_name}</td>
            <td><span class="badge {status_badge}">{p.status}</span></td>
            <td>{tasks_count}</td>
            <td>
                <form method="post" action="/admin/projects/{p.id}/delete" style="display:inline" onsubmit="return confirm('Удалить проект?')">
                    <button class="btn btn-sm btn-outline-danger"><i class="fas fa-trash"></i></button>
                </form>
            </td>
        </tr>
        """
    
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Управление проектами</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        {BASE_STYLE}
    </head>
    <body class="bg-light">
        <nav class="navbar navbar-expand-lg navbar-dark bg-dark sticky-top">
            <div class="container">
                <a class="navbar-brand" href="/admin"><i class="fas fa-crown"></i> Админ</a>
                <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                    <span class="navbar-toggler-icon"></span>
                </button>
                <div class="collapse navbar-collapse" id="navbarNav">
                    <ul class="navbar-nav ms-auto">
                        <li class="nav-item"><a class="nav-link" href="/admin"><i class="fas fa-dashboard"></i> Дашборд</a></li>
                        <li class="nav-item"><a class="nav-link" href="/admin/users"><i class="fas fa-users"></i> Пользователи</a></li>
                        <li class="nav-item"><a class="nav-link active" href="/admin/projects"><i class="fas fa-folder"></i> Проекты</a></li>
                        <li class="nav-item"><a class="nav-link" href="/projects"><i class="fas fa-arrow-left"></i> На сайт</a></li>
                        <li class="nav-item"><a class="nav-link" href="/logout"><i class="fas fa-sign-out-alt"></i> Выйти</a></li>
                    </ul>
                </div>
            </div>
        </nav>
        <div class="container mt-3">
            <h5><i class="fas fa-folder text-primary"></i> Проекты</h5>
            <hr>
            <div class="card shadow">
                <div class="card-body table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Название</th>
                                <th>Владелец</th>
                                <th>Статус</th>
                                <th>Задачи</th>
                                <th>Действия</th>
                            </tr>
                        </thead>
                        <tbody>
                            {projects_html}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """)

@app.post("/admin/projects/{project_id}/delete")
async def admin_delete_project(project_id: int, request: Request, db: Session = Depends(get_db)):
    admin_user = get_current_user(request, db)
    if not admin_user or not is_admin(admin_user):
        return HTMLResponse("<div class='container mt-4'><div class='alert alert-danger'>403 Доступ запрещен</div></div>")
    project = db.query(Project).filter(Project.id == project_id).first()
    if project:
        db.delete(project)
        db.commit()
    return RedirectResponse("/admin/projects", status_code=303)

# ==================== ВЫХОД ====================

@app.get("/logout")
async def logout():
    response = RedirectResponse("/login")
    response.delete_cookie("access_token")
    return response

# ==================== ЗАПУСК ====================

if __name__ == "__main__":
    db = SessionLocal()
    create_first_admin(db)
    db.close()
    
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)