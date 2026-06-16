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

# ==================== HTML СТРАНИЦЫ ====================

REGISTER_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Регистрация</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <div class="container mt-5">
        <div class="row justify-content-center">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h3>Регистрация</h3>
                    </div>
                    <div class="card-body">
                        <form method="post">
                            <div class="mb-3">
                                <label>Email</label>
                                <input type="email" name="email" class="form-control" required>
                            </div>
                            <div class="mb-3">
                                <label>Имя пользователя</label>
                                <input type="text" name="username" class="form-control" required>
                            </div>
                            <div class="mb-3">
                                <label>Полное имя</label>
                                <input type="text" name="full_name" class="form-control">
                            </div>
                            <div class="mb-3">
                                <label>Пароль</label>
                                <input type="password" name="password" class="form-control" required>
                            </div>
                            <button type="submit" class="btn btn-primary w-100">Зарегистрироваться</button>
                        </form>
                        <hr>
                        <p class="text-center">Уже есть аккаунт? <a href="/login">Войти</a></p>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

LOGIN_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Вход</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <div class="container mt-5">
        <div class="row justify-content-center">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header bg-success text-white">
                        <h3>Вход в систему</h3>
                    </div>
                    <div class="card-body">
                        <form method="post">
                            <div class="mb-3">
                                <label>Имя пользователя</label>
                                <input type="text" name="username" class="form-control" required>
                            </div>
                            <div class="mb-3">
                                <label>Пароль</label>
                                <input type="password" name="password" class="form-control" required>
                            </div>
                            <button type="submit" class="btn btn-success w-100">Войти</button>
                        </form>
                        <hr>
                        <p class="text-center"><a href="/forgot-password">Забыли пароль?</a></p>
                        <p class="text-center">Нет аккаунта? <a href="/register">Зарегистрироваться</a></p>
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
        return HTMLResponse(content="<h3>Пользователь уже существует! <a href='/register'>Назад</a></h3>")
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
        return HTMLResponse(content="<h3>Неверный логин или пароль! <a href='/login'>Назад</a></h3>")
    token = create_access_token(data={"sub": user.username})
    response = RedirectResponse("/projects", status_code=303)
    response.set_cookie(key="access_token", value=token, httponly=True)
    return response

@app.get("/profile")
async def profile(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    
    unread_count = db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read == False).count()
    admin_link = '<a class="nav-link" href="/admin"><i class="fas fa-crown"></i> Админ-панель</a>' if is_admin(user) else ''
    
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Личный кабинет</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    </head>
    <body>
        <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
            <div class="container">
                <a class="navbar-brand" href="/projects"><i class="fas fa-tasks"></i> ProjectManager</a>
                <div class="navbar-nav ms-auto">
                    <a class="nav-link" href="/projects"><i class="fas fa-folder"></i> Проекты</a>
                    <a class="nav-link" href="/tasks"><i class="fas fa-check-square"></i> Задачи</a>
                    <a class="nav-link active" href="/profile"><i class="fas fa-user"></i> Профиль</a>
                    <a class="nav-link" href="/notifications">
                        <i class="fas fa-bell"></i>
                        <span class="badge bg-danger">{unread_count}</span>
                    </a>
                    {admin_link}
                    <a class="nav-link" href="/logout"><i class="fas fa-sign-out-alt"></i> Выйти</a>
                </div>
            </div>
        </nav>
        <div class="container mt-4">
            <div class="row">
                <div class="col-md-6 mx-auto">
                    <div class="card shadow">
                        <div class="card-header bg-info text-white">
                            <h4><i class="fas fa-id-card"></i> Личный кабинет</h4>
                        </div>
                        <div class="card-body">
                            <table class="table">
                                <tr><td><strong>Имя пользователя:</strong></td><td>{user.username}</td></tr>
                                <tr><td><strong>Полное имя:</strong></td><td>{user.full_name or "Не указано"}</td></tr>
                                <tr><td><strong>Email:</strong></td><td>{user.email}</td></tr>
                                <tr><td><strong>Роль:</strong></td><td>{user.role}</td></tr>
                                <tr><td><strong>Дата регистрации:</strong></td><td>{user.created_at}</td></tr>
                                <tr><td><strong>Уведомлений:</strong></td><td><span class="badge bg-danger">{unread_count}</span> непрочитанных</td></tr>
                            </table>
                            <div class="d-grid gap-2">
                                <a href="/profile/edit" class="btn btn-warning"><i class="fas fa-edit"></i> Редактировать профиль</a>
                                <a href="/profile/change-password" class="btn btn-danger"><i class="fas fa-key"></i> Сменить пароль</a>
                                <a href="/notifications" class="btn btn-info"><i class="fas fa-bell"></i> Уведомления ({unread_count})</a>
                                <a href="/activity" class="btn btn-secondary"><i class="fas fa-history"></i> Моя активность</a>
                                {'<a href="/admin" class="btn btn-danger"><i class="fas fa-crown"></i> Админ-панель</a>' if is_admin(user) else ''}
                                <a href="/projects" class="btn btn-primary"><i class="fas fa-arrow-left"></i> Назад к проектам</a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """)

@app.get("/profile/edit")
async def edit_profile_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    return HTMLResponse(content=f"""
    <form method="post" action="/profile/edit">
        <input type="email" name="email" value="{user.email}" required>
        <input type="text" name="username" value="{user.username}" required>
        <input type="text" name="full_name" value="{user.full_name or ''}">
        <button type="submit">Сохранить</button>
    </form>
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
    return HTMLResponse(content="""
    <form method="post">
        <input type="password" name="old_password" placeholder="Текущий пароль" required>
        <input type="password" name="new_password" placeholder="Новый пароль" required>
        <input type="password" name="confirm_password" placeholder="Подтверждение" required>
        <button type="submit">Сменить пароль</button>
    </form>
    """)

@app.post("/profile/change-password")
async def change_password(request: Request, old_password: str = Form(...), new_password: str = Form(...), confirm_password: str = Form(...), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    if new_password != confirm_password:
        return HTMLResponse("<h3>Пароли не совпадают!</h3>")
    if not verify_password(old_password, user.hashed_password):
        return HTMLResponse("<h3>Неверный текущий пароль!</h3>")
    user.hashed_password = hash_password(new_password)
    db.commit()
    return HTMLResponse("<h3>Пароль изменен! <a href='/profile'>В профиль</a></h3>")

@app.get("/forgot-password")
async def forgot_password_page():
    return HTMLResponse("""
    <form method="post">
        <input type="email" name="email" placeholder="Email" required>
        <button type="submit">Отправить ссылку</button>
    </form>
    """)

@app.post("/forgot-password")
async def forgot_password(email: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if user:
        token = generate_reset_token()
        user.reset_token = token
        user.reset_token_expires = str(datetime.now() + timedelta(hours=1))
        db.commit()
        return HTMLResponse(f"<a href='/reset-password?token={token}'>Сбросить пароль</a>")
    return HTMLResponse("<h3>Email не найден!</h3>")

@app.get("/reset-password")
async def reset_password_page(token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.reset_token == token).first()
    if not user:
        return HTMLResponse("<h3>Неверная ссылка!</h3>")
    return HTMLResponse(f"""
    <form method="post" action="/reset-password">
        <input type="hidden" name="token" value="{token}">
        <input type="password" name="new_password" placeholder="Новый пароль" required>
        <input type="password" name="confirm_password" placeholder="Подтверждение" required>
        <button type="submit">Сохранить</button>
    </form>
    """)

@app.post("/reset-password")
async def reset_password(token: str = Form(...), new_password: str = Form(...), confirm_password: str = Form(...), db: Session = Depends(get_db)):
    if new_password != confirm_password:
        return HTMLResponse("<h3>Пароли не совпадают!</h3>")
    user = db.query(User).filter(User.reset_token == token).first()
    if not user:
        return HTMLResponse("<h3>Неверная ссылка!</h3>")
    user.hashed_password = hash_password(new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()
    return HTMLResponse("<h3>Пароль изменен! <a href='/login'>Войти</a></h3>")

# ==================== ПРОЕКТЫ ====================

@app.get("/projects")
async def projects_list(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    
    admin_link = '<a class="nav-link" href="/admin"><i class="fas fa-crown"></i> Админ-панель</a>' if is_admin(user) else ''
    
    projects = db.query(Project).filter(Project.owner_id == user.id).all()
    
    projects_html = ""
    for p in projects:
        projects_html += f"""
        <div class="col-md-6 mb-2">
            <div class="card">
                <div class="card-body">
                    <h5>{p.name}</h5>
                    <p>{p.description[:100] if p.description else ""}</p>
                    <a href="/projects/{p.id}/tasks" class="btn btn-sm btn-primary">Задачи</a>
                </div>
            </div>
        </div>
        """
    
    if not projects_html:
        projects_html = '<div class="alert alert-info">Нет проектов</div>'
    
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Мои проекты</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <nav class="navbar navbar-dark bg-dark">
            <div class="container">
                <a class="navbar-brand" href="/projects">ProjectManager</a>
                <div class="navbar-nav ms-auto">
                    <a class="nav-link" href="/tasks">Задачи</a>
                    <a class="nav-link" href="/profile">Профиль</a>
                    {admin_link}
                    <a class="nav-link" href="/logout">Выйти</a>
                </div>
            </div>
        </nav>
        <div class="container mt-4">
            <div class="row">
                <div class="col-md-4">
                    <div class="card">
                        <div class="card-header bg-success text-white">Создать проект</div>
                        <div class="card-body">
                            <form method="post" action="/projects/create">
                                <input type="text" name="name" class="form-control mb-2" placeholder="Название" required>
                                <textarea name="description" class="form-control mb-2" placeholder="Описание"></textarea>
                                <select name="status" class="form-select mb-2">
                                    <option value="active">Активный</option>
                                    <option value="completed">Завершен</option>
                                    <option value="archived">Архив</option>
                                </select>
                                <button type="submit" class="btn btn-success w-100">Создать</button>
                            </form>
                        </div>
                    </div>
                </div>
                <div class="col-md-8">
                    <div class="card">
                        <div class="card-header bg-primary text-white">Мои проекты</div>
                        <div class="card-body">
                            <div class="row">
                                {projects_html}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
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
    
    admin_link = '<a class="nav-link" href="/admin"><i class="fas fa-crown"></i> Админ-панель</a>' if is_admin(user) else ''
    
    tasks = db.query(Task).filter(Task.created_by == user.id).order_by(desc(Task.created_at)).all()
    
    projects = db.query(Project).filter(Project.owner_id == user.id).all()
    projects_options = ""
    for p in projects:
        projects_options += f'<option value="{p.id}">{p.name}</option>'
    
    tasks_html = ""
    for t in tasks:
        status_badge = "bg-secondary" if t.status == "todo" else "bg-primary" if t.status == "in_progress" else "bg-warning" if t.status == "review" else "bg-success"
        status_text = "To Do" if t.status == "todo" else "В работе" if t.status == "in_progress" else "На проверке" if t.status == "review" else "Выполнено"
        tasks_html += f"""
        <div class="col-md-4 mb-2">
            <div class="card">
                <div class="card-body">
                    <h6><a href="/tasks/{t.id}">{t.title}</a></h6>
                    <span class="badge {status_badge}">{status_text}</span>
                    <p class="small mt-2">{t.description[:50] if t.description else ""}</p>
                </div>
            </div>
        </div>
        """
    
    if not tasks_html:
        tasks_html = '<div class="col-12"><div class="alert alert-info">Нет задач. Создайте первую задачу!</div></div>'
    
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Мои задачи</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    </head>
    <body>
        <nav class="navbar navbar-dark bg-dark">
            <div class="container">
                <a class="navbar-brand" href="/projects">ProjectManager</a>
                <div class="navbar-nav ms-auto">
                    <a class="nav-link" href="/projects">Проекты</a>
                    <a class="nav-link active" href="/tasks">Задачи</a>
                    <a class="nav-link" href="/profile">Профиль</a>
                    {admin_link}
                    <a class="nav-link" href="/logout">Выйти</a>
                </div>
            </div>
        </nav>
        <div class="container mt-4">
            <div class="row">
                <div class="col-md-4">
                    <div class="card">
                        <div class="card-header bg-success text-white">
                            <h5><i class="fas fa-plus"></i> Создать задачу</h5>
                        </div>
                        <div class="card-body">
                            <form method="post" action="/tasks/create">
                                <div class="mb-2">
                                    <label>Название</label>
                                    <input type="text" name="title" class="form-control" required>
                                </div>
                                <div class="mb-2">
                                    <label>Описание</label>
                                    <textarea name="description" class="form-control" rows="2"></textarea>
                                </div>
                                <div class="mb-2">
                                    <label>Проект</label>
                                    <select name="project_id" class="form-select" required>
                                        <option value="">Выберите проект</option>
                                        {projects_options}
                                    </select>
                                </div>
                                <div class="row">
                                    <div class="col-6">
                                        <div class="mb-2">
                                            <label>Статус</label>
                                            <select name="status" class="form-select">
                                                <option value="todo">To Do</option>
                                                <option value="in_progress">В работе</option>
                                                <option value="review">На проверке</option>
                                                <option value="done">Выполнено</option>
                                            </select>
                                        </div>
                                    </div>
                                    <div class="col-6">
                                        <div class="mb-2">
                                            <label>Приоритет</label>
                                            <select name="priority" class="form-select">
                                                <option value="low">Низкий</option>
                                                <option value="medium" selected>Средний</option>
                                                <option value="high">Высокий</option>
                                                <option value="urgent">Срочный</option>
                                            </select>
                                        </div>
                                    </div>
                                </div>
                                <button type="submit" class="btn btn-success w-100">Создать</button>
                            </form>
                        </div>
                    </div>
                </div>
                <div class="col-md-8">
                    <div class="card">
                        <div class="card-header bg-primary text-white">
                            <h5><i class="fas fa-list"></i> Мои задачи</h5>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                {tasks_html}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
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
    
    add_activity(
        user_id=user.id,
        action="Создал задачу",
        details=f"'{title}' в проекте",
        task_id=new_task.id,
        project_id=project_id,
        db=db
    )
    
    return RedirectResponse("/tasks", status_code=303)

@app.get("/tasks/{task_id}")
async def task_detail(task_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return HTMLResponse("<h3>Задача не найдена!</h3>")
    
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
    
    activities = db.query(ActivityLog).filter(ActivityLog.task_id == task_id).order_by(desc(ActivityLog.created_at)).limit(10).all()
    activity_html = ""
    for a in activities:
        activity_html += f"""
        <div class="border-bottom p-2 small">
            <span>{a.action}: {a.details[:50]}</span>
            <br><small class="text-muted">{a.created_at}</small>
        </div>
        """
    
    if not activity_html:
        activity_html = '<p class="text-muted">Нет активности</p>'
    
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
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    </head>
    <body>
        <nav class="navbar navbar-dark bg-dark">
            <div class="container">
                <a class="navbar-brand" href="/projects">ProjectManager</a>
                <div class="navbar-nav ms-auto">
                    <a class="nav-link" href="/tasks">← Все задачи</a>
                    <a class="nav-link" href="/logout">Выйти</a>
                </div>
            </div>
        </nav>
        <div class="container mt-4">
            <div class="row">
                <div class="col-md-8">
                    <div class="card">
                        <div class="card-header bg-primary text-white">
                            <h4>{task.title}</h4>
                        </div>
                        <div class="card-body">
                            <p><strong>Описание:</strong> {task.description or "Нет описания"}</p>
                            <p><strong>Статус:</strong> {status_names.get(task.status, task.status)}</p>
                            <p><strong>Приоритет:</strong> {priority_names.get(task.priority, task.priority)}</p>
                            <p><strong>Проект:</strong> {project.name if project else "Без проекта"}</p>
                            <p><strong>Создал:</strong> {creator.username if creator else "Unknown"}</p>
                            <p><strong>Исполнитель:</strong> {assignee.username if assignee else "Не назначен"}</p>
                            <p><strong>Создана:</strong> {task.created_at}</p>
                            <div class="mt-3">
                                <a href="/tasks/{task.id}/edit" class="btn btn-warning">Редактировать</a>
                                <a href="/tasks/{task.id}/delete" class="btn btn-danger" onclick="return confirm('Удалить?')">Удалить</a>
                            </div>
                        </div>
                    </div>
                    
                    <div class="card mt-4">
                        <div class="card-header bg-secondary text-white">
                            <h5><i class="fas fa-comments"></i> Комментарии ({len(comments)})</h5>
                        </div>
                        <div class="card-body">
                            {comments_html}
                            <hr>
                            <form method="post" action="/tasks/{task.id}/comment">
                                <div class="input-group">
                                    <input type="text" name="content" class="form-control" placeholder="Написать комментарий..." required>
                                    <button type="submit" class="btn btn-primary">Отправить</button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card">
                        <div class="card-header bg-info text-white">
                            <h5><i class="fas fa-history"></i> Активность</h5>
                        </div>
                        <div class="card-body">
                            {activity_html}
                        </div>
                    </div>
                </div>
            </div>
        </div>
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
    
    add_activity(
        user_id=user.id,
        action="Добавил комментарий",
        details=f"К задаче '{task.title}'",
        task_id=task_id,
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
        return HTMLResponse("<h3>Задача не найдена!</h3>")
    
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
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    </head>
    <body class="bg-light">
        <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
            <div class="container">
                <a class="navbar-brand" href="/projects"><i class="fas fa-tasks"></i> ProjectManager</a>
                <div class="navbar-nav ms-auto">
                    <a class="nav-link" href="/projects"><i class="fas fa-folder"></i> Проекты</a>
                    <a class="nav-link" href="/tasks"><i class="fas fa-check-square"></i> Задачи</a>
                    <a class="nav-link" href="/profile"><i class="fas fa-user"></i> Профиль</a>
                    <a class="nav-link" href="/logout"><i class="fas fa-sign-out-alt"></i> Выйти</a>
                </div>
            </div>
        </nav>
        <div class="container mt-4">
            <div class="row justify-content-center">
                <div class="col-md-8">
                    <div class="card shadow">
                        <div class="card-header bg-warning text-dark">
                            <h4><i class="fas fa-edit"></i> Редактирование задачи</h4>
                        </div>
                        <div class="card-body">
                            <form method="post" action="/tasks/{task_id}/edit">
                                <div class="mb-3">
                                    <label class="form-label"><i class="fas fa-heading"></i> Название <span class="text-danger">*</span></label>
                                    <input type="text" name="title" class="form-control form-control-lg" value="{task.title}" required>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label"><i class="fas fa-align-left"></i> Описание</label>
                                    <textarea name="description" class="form-control" rows="4">{task.description or ""}</textarea>
                                </div>
                                <div class="row">
                                    <div class="col-md-6">
                                        <div class="mb-3">
                                            <label class="form-label"><i class="fas fa-circle"></i> Статус</label>
                                            <select name="status" class="form-select">
                                                <option value="todo" {'selected' if task.status == 'todo' else ''}>📋 To Do</option>
                                                <option value="in_progress" {'selected' if task.status == 'in_progress' else ''}>🔄 В работе</option>
                                                <option value="review" {'selected' if task.status == 'review' else ''}>👀 На проверке</option>
                                                <option value="done" {'selected' if task.status == 'done' else ''}>✅ Выполнено</option>
                                            </select>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="mb-3">
                                            <label class="form-label"><i class="fas fa-flag"></i> Приоритет</label>
                                            <select name="priority" class="form-select">
                                                <option value="low" {'selected' if task.priority == 'low' else ''}>🟢 Низкий</option>
                                                <option value="medium" {'selected' if task.priority == 'medium' else ''}>🟡 Средний</option>
                                                <option value="high" {'selected' if task.priority == 'high' else ''}>🔴 Высокий</option>
                                                <option value="urgent" {'selected' if task.priority == 'urgent' else ''}>⚡ Срочный</option>
                                            </select>
                                        </div>
                                    </div>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label"><i class="fas fa-folder"></i> Проект <span class="text-danger">*</span></label>
                                    <select name="project_id" class="form-select" required>
                                        {projects_options}
                                    </select>
                                </div>
                                <div class="d-grid gap-2 d-md-flex justify-content-md-end">
                                    <a href="/tasks" class="btn btn-secondary">
                                        <i class="fas fa-times"></i> Отмена
                                    </a>
                                    <button type="submit" class="btn btn-warning">
                                        <i class="fas fa-save"></i> Сохранить
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                    <div class="card shadow mt-3">
                        <div class="card-header bg-light">
                            <h6><i class="fas fa-info-circle"></i> Информация о задаче</h6>
                        </div>
                        <div class="card-body">
                            <div class="row text-muted small">
                                <div class="col-md-4">
                                    <i class="fas fa-user"></i> Создал: {user.username}
                                </div>
                                <div class="col-md-4">
                                    <i class="fas fa-calendar"></i> Создана: {task.created_at}
                                </div>
                                <div class="col-md-4">
                                    <i class="fas fa-clock"></i> Обновлена: {task.updated_at}
                                </div>
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
        
        add_activity(
            user_id=user.id,
            action="Обновил задачу",
            details=f"'{title}'",
            task_id=task_id,
            project_id=project_id,
            db=db
        )
    
    return RedirectResponse("/tasks", status_code=303)

@app.get("/tasks/{task_id}/delete")
async def delete_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    
    task = db.query(Task).filter(Task.id == task_id, Task.created_by == user.id).first()
    if task:
        task_title = task.title
        db.delete(task)
        db.commit()
        
        add_activity(
            user_id=user.id,
            action="Удалил задачу",
            details=f"'{task_title}'",
            db=db
        )
    
    return RedirectResponse("/tasks", status_code=303)

@app.get("/tasks/{task_id}/status/{new_status}")
async def update_task_status(task_id: int, new_status: str, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    
    task = db.query(Task).filter(Task.id == task_id, Task.created_by == user.id).first()
    if task:
        old_status = task.status
        task.status = new_status
        task.updated_at = str(datetime.now())
        db.commit()
        
        add_activity(
            user_id=user.id,
            action="Изменил статус задачи",
            details=f"'{task.title}' с {old_status} на {new_status}",
            task_id=task_id,
            db=db
        )
    
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
    
    status_colors = {
        "todo": "secondary",
        "in_progress": "primary",
        "review": "warning",
        "done": "success"
    }
    status_texts = {
        "todo": "To Do",
        "in_progress": "В работе",
        "review": "На проверке",
        "done": "Выполнено"
    }
    
    tasks_html = ""
    if tasks:
        for t in tasks:
            status_color = status_colors.get(t.status, "secondary")
            status_text = status_texts.get(t.status, t.status)
            tasks_html += f"""
            <div class="col-md-6 mb-3">
                <div class="card shadow-sm h-100">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start">
                            <h5 class="card-title">{t.title}</h5>
                            <span class="badge bg-{status_color}">{status_text}</span>
                        </div>
                        <p class="card-text text-muted mt-2">{t.description[:100] if t.description else "Нет описания"}</p>
                        <div class="mt-3">
                            <a href="/tasks/{t.id}" class="btn btn-sm btn-outline-primary">Открыть</a>
                            <a href="/tasks/{t.id}/edit" class="btn btn-sm btn-outline-warning">Редактировать</a>
                            <a href="/tasks/{t.id}/delete" class="btn btn-sm btn-outline-danger" onclick="return confirm('Удалить?')">Удалить</a>
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
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    </head>
    <body>
        <nav class="navbar navbar-dark bg-dark">
            <div class="container">
                <a class="navbar-brand" href="/projects">ProjectManager</a>
                <div class="navbar-nav ms-auto">
                    <a class="nav-link" href="/projects">Проекты</a>
                    <a class="nav-link" href="/logout">Выйти</a>
                </div>
            </div>
        </nav>
        <div class="container mt-4">
            <h2><i class="fas fa-project-diagram"></i> {project.name}</h2>
            <p class="text-muted">{project.description or "Описание отсутствует"}</p>
            <hr>
            <div class="row">
                {tasks_html}
            </div>
            <a href="/projects" class="btn btn-secondary mt-3">← Назад</a>
        </div>
    </body>
    </html>
    """)

# ==================== УВЕДОМЛЕНИЯ И АКТИВНОСТЬ ====================

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
        <div class="card mb-2 border-{type_color}">
            <div class="card-body">
                <div class="d-flex justify-content-between">
                    <h6>{n.title} {is_read}</h6>
                    <small class="text-muted">{n.created_at}</small>
                </div>
                <p>{n.message}</p>
                <div>
                    <a href="/notifications/{n.id}/read" class="btn btn-sm btn-outline-primary">Прочитано</a>
                    {f'<a href="{n.link}" class="btn btn-sm btn-outline-secondary">Перейти</a>' if n.link else ''}
                </div>
            </div>
        </div>
        """
    
    if not notifications_html:
        notifications_html = '<div class="alert alert-info">У вас нет уведомлений</div>'
    
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Уведомления</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    </head>
    <body>
        <nav class="navbar navbar-dark bg-dark">
            <div class="container">
                <a class="navbar-brand" href="/projects">ProjectManager</a>
                <div class="navbar-nav ms-auto">
                    <a class="nav-link" href="/profile">Профиль</a>
                    <a class="nav-link" href="/logout">Выйти</a>
                </div>
            </div>
        </nav>
        <div class="container mt-4">
            <div class="d-flex justify-content-between">
                <h1><i class="fas fa-bell"></i> Уведомления</h1>
                <a href="/notifications/mark-all-read" class="btn btn-secondary">Все прочитаны</a>
            </div>
            <hr>
            <div class="row">
                <div class="col-md-12">
                    {notifications_html}
                </div>
            </div>
        </div>
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
            <p>{a.details}</p>
            <small class="text-muted">{a.created_at}</small>
        </div>
        """
    
    if not activity_html:
        activity_html = '<div class="alert alert-info">Нет активности</div>'
    
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Моя активность</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    </head>
    <body>
        <nav class="navbar navbar-dark bg-dark">
            <div class="container">
                <a class="navbar-brand" href="/projects">ProjectManager</a>
                <div class="navbar-nav ms-auto">
                    <a class="nav-link" href="/profile">Профиль</a>
                    <a class="nav-link" href="/logout">Выйти</a>
                </div>
            </div>
        </nav>
        <div class="container mt-4">
            <h1><i class="fas fa-history"></i> Моя активность</h1>
            <hr>
            <div class="row">
                <div class="col-md-12">
                    {activity_html}
                </div>
            </div>
        </div>
    </body>
    </html>
    """)

# ==================== АДМИН-ПАНЕЛЬ ====================

ADMIN_DASHBOARD_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Админ-панель</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
</head>
<body class="bg-light">
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="/admin"><i class="fas fa-crown"></i> Админ-панель</a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="/admin"><i class="fas fa-dashboard"></i> Дашборд</a>
                <a class="nav-link" href="/admin/users"><i class="fas fa-users"></i> Пользователи</a>
                <a class="nav-link" href="/admin/projects"><i class="fas fa-folder"></i> Проекты</a>
                <a class="nav-link" href="/projects"><i class="fas fa-arrow-left"></i> На сайт</a>
                <a class="nav-link" href="/logout"><i class="fas fa-sign-out-alt"></i> Выйти</a>
            </div>
        </div>
    </nav>
    <div class="container mt-4">
        <h1><i class="fas fa-dashboard text-primary"></i> Панель управления</h1>
        <p class="text-muted">Добро пожаловать в административную панель, {username}!</p>
        <div class="row mt-4">
            <div class="col-md-3">
                <div class="card text-white bg-primary shadow">
                    <div class="card-body">
                        <h5><i class="fas fa-users"></i> Пользователи</h5>
                        <h2>{total_users}</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-white bg-success shadow">
                    <div class="card-body">
                        <h5><i class="fas fa-folder"></i> Проекты</h5>
                        <h2>{total_projects}</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-white bg-warning shadow">
                    <div class="card-body">
                        <h5><i class="fas fa-tasks"></i> Задачи</h5>
                        <h2>{total_tasks}</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-white bg-info shadow">
                    <div class="card-body">
                        <h5><i class="fas fa-comments"></i> Комментарии</h5>
                        <h2>{total_comments}</h2>
                    </div>
                </div>
            </div>
        </div>
        <div class="card shadow mt-4">
            <div class="card-header bg-dark text-white">
                <h5><i class="fas fa-clock"></i> Последняя активность</h5>
            </div>
            <div class="card-body">
                {activity_html}
            </div>
        </div>
    </div>
</body>
</html>
"""

ADMIN_USERS_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Управление пользователями</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
</head>
<body class="bg-light">
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="/admin"><i class="fas fa-crown"></i> Админ-панель</a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="/admin"><i class="fas fa-dashboard"></i> Дашборд</a>
                <a class="nav-link active" href="/admin/users"><i class="fas fa-users"></i> Пользователи</a>
                <a class="nav-link" href="/admin/projects"><i class="fas fa-folder"></i> Проекты</a>
                <a class="nav-link" href="/projects"><i class="fas fa-arrow-left"></i> На сайт</a>
                <a class="nav-link" href="/logout"><i class="fas fa-sign-out-alt"></i> Выйти</a>
            </div>
        </div>
    </nav>
    <div class="container mt-4">
        <h1><i class="fas fa-users text-primary"></i> Пользователи</h1>
        <hr>
        <div class="card shadow">
            <div class="card-body">
                <table class="table table-hover">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Имя пользователя</th>
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
</body>
</html>
"""

ADMIN_PROJECTS_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Управление проектами</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
</head>
<body class="bg-light">
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="/admin"><i class="fas fa-crown"></i> Админ-панель</a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="/admin"><i class="fas fa-dashboard"></i> Дашборд</a>
                <a class="nav-link" href="/admin/users"><i class="fas fa-users"></i> Пользователи</a>
                <a class="nav-link active" href="/admin/projects"><i class="fas fa-folder"></i> Проекты</a>
                <a class="nav-link" href="/projects"><i class="fas fa-arrow-left"></i> На сайт</a>
                <a class="nav-link" href="/logout"><i class="fas fa-sign-out-alt"></i> Выйти</a>
            </div>
        </div>
    </nav>
    <div class="container mt-4">
        <h1><i class="fas fa-folder text-primary"></i> Проекты</h1>
        <hr>
        <div class="card shadow">
            <div class="card-body">
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
</body>
</html>
"""

# ==================== АДМИН МАРШРУТЫ ====================

@app.get("/admin")
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or not is_admin(user):
        return HTMLResponse("<h1>403 Доступ запрещен</h1><p>Только для администраторов</p>")
    
    total_users = db.query(User).count()
    total_projects = db.query(Project).count()
    total_tasks = db.query(Task).count()
    total_comments = db.query(Comment).count()
    
    activities = db.query(ActivityLog).order_by(desc(ActivityLog.created_at)).limit(10).all()
    activity_html = ""
    for a in activities:
        user_obj = db.query(User).filter(User.id == a.user_id).first()
        username = user_obj.username if user_obj else "Unknown"
        activity_html += f"""
        <div class="border-bottom p-2">
            <strong>{username}</strong> - {a.action}
            <p class="small text-muted">{a.details}</p>
            <small>{a.created_at}</small>
        </div>
        """
    
    if not activity_html:
        activity_html = '<p class="text-muted">Нет активности</p>'
    
    return HTMLResponse(content=ADMIN_DASHBOARD_PAGE.format(
        username=user.username,
        total_users=total_users,
        total_projects=total_projects,
        total_tasks=total_tasks,
        total_comments=total_comments,
        activity_html=activity_html
    ))

@app.get("/admin/users")
async def admin_users(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or not is_admin(user):
        return HTMLResponse("<h1>403 Доступ запрещен</h1>")
    
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
                <form method="post" action="/admin/users/{u.id}/toggle" style="display:inline">
                    <button class="btn btn-sm btn-outline-warning">
                        {'Деактивировать' if u.is_active else 'Активировать'}
                    </button>
                </form>
                <form method="post" action="/admin/users/{u.id}/make-admin" style="display:inline">
                    <button class="btn btn-sm btn-outline-primary">Сделать админом</button>
                </form>
            </td>
        </tr>
        """
    
    return HTMLResponse(content=ADMIN_USERS_PAGE.format(users_html=users_html))

@app.post("/admin/users/{user_id}/toggle")
async def admin_toggle_user(user_id: int, request: Request, db: Session = Depends(get_db)):
    admin_user = get_current_user(request, db)
    if not admin_user or not is_admin(admin_user):
        return HTMLResponse("<h1>403 Доступ запрещен</h1>")
    
    target_user = db.query(User).filter(User.id == user_id).first()
    if target_user:
        target_user.is_active = not target_user.is_active
        db.commit()
    return RedirectResponse("/admin/users", status_code=303)

@app.post("/admin/users/{user_id}/make-admin")
async def admin_make_admin(user_id: int, request: Request, db: Session = Depends(get_db)):
    admin_user = get_current_user(request, db)
    if not admin_user or not is_admin(admin_user):
        return HTMLResponse("<h1>403 Доступ запрещен</h1>")
    
    target_user = db.query(User).filter(User.id == user_id).first()
    if target_user:
        target_user.role = "admin"
        db.commit()
    return RedirectResponse("/admin/users", status_code=303)

@app.get("/admin/projects")
async def admin_projects(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or not is_admin(user):
        return HTMLResponse("<h1>403 Доступ запрещен</h1>")
    
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
                    <button class="btn btn-sm btn-outline-danger">Удалить</button>
                </form>
            </td>
        </tr>
        """
    
    return HTMLResponse(content=ADMIN_PROJECTS_PAGE.format(projects_html=projects_html))

@app.post("/admin/projects/{project_id}/delete")
async def admin_delete_project(project_id: int, request: Request, db: Session = Depends(get_db)):
    admin_user = get_current_user(request, db)
    if not admin_user or not is_admin(admin_user):
        return HTMLResponse("<h1>403 Доступ запрещен</h1>")
    
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
    uvicorn.run(app, host="127.0.0.1", port=8000)