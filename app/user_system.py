from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
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

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True)
    name = Column(String, index=True)
    description = Column(Text, default="")
    status = Column(String, default="active")
    owner_id = Column(Integer)
    created_at = Column(String, default=str(datetime.now()))
    updated_at = Column(String, default=str(datetime.now()))

Base.metadata.create_all(bind=engine)

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

PROFILE_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Личный кабинет</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="/projects">ProjectManager</a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="/projects">Проекты</a>
                <a class="nav-link active" href="/profile">Профиль</a>
                <a class="nav-link" href="/logout">Выйти</a>
            </div>
        </div>
    </nav>
    <div class="container mt-4">
        <div class="row">
            <div class="col-md-6 mx-auto">
                <div class="card">
                    <div class="card-header bg-info text-white">
                        <h4>Личный кабинет</h4>
                    </div>
                    <div class="card-body">
                        <table class="table">
                            <tr><td><strong>Имя пользователя:</strong></td><td>{username}</td></tr>
                            <tr><td><strong>Полное имя:</strong></td><td>{full_name}</td></tr>
                            <tr><td><strong>Email:</strong></td><td>{email}</td></tr>
                            <tr><td><strong>Роль:</strong></td><td>{role}</td></tr>
                            <tr><td><strong>Дата регистрации:</strong></td><td>{created_at}</td></tr>
                        </table>
                        <div class="d-grid gap-2">
                            <a href="/profile/edit" class="btn btn-warning">Редактировать профиль</a>
                            <a href="/profile/change-password" class="btn btn-danger">Сменить пароль</a>
                            <a href="/projects" class="btn btn-secondary">Назад к проектам</a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

EDIT_PROFILE_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Редактирование профиля</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="/projects">ProjectManager</a>
        </div>
    </nav>
    <div class="container mt-4">
        <div class="row justify-content-center">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header bg-warning">
                        <h4>Редактирование профиля</h4>
                    </div>
                    <div class="card-body">
                        <form method="post">
                            <div class="mb-3">
                                <label>Email</label>
                                <input type="email" name="email" class="form-control" value="{email}" required>
                            </div>
                            <div class="mb-3">
                                <label>Имя пользователя</label>
                                <input type="text" name="username" class="form-control" value="{username}" required>
                            </div>
                            <div class="mb-3">
                                <label>Полное имя</label>
                                <input type="text" name="full_name" class="form-control" value="{full_name}">
                            </div>
                            <button type="submit" class="btn btn-warning w-100">Сохранить</button>
                            <a href="/profile" class="btn btn-secondary w-100 mt-2">Отмена</a>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

CHANGE_PASSWORD_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Смена пароля</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="/projects">ProjectManager</a>
        </div>
    </nav>
    <div class="container mt-4">
        <div class="row justify-content-center">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header bg-danger text-white">
                        <h4>Смена пароля</h4>
                    </div>
                    <div class="card-body">
                        <form method="post">
                            <div class="mb-3">
                                <label>Текущий пароль</label>
                                <input type="password" name="old_password" class="form-control" required>
                            </div>
                            <div class="mb-3">
                                <label>Новый пароль</label>
                                <input type="password" name="new_password" class="form-control" required>
                            </div>
                            <div class="mb-3">
                                <label>Подтверждение пароля</label>
                                <input type="password" name="confirm_password" class="form-control" required>
                            </div>
                            <button type="submit" class="btn btn-danger w-100">Сменить пароль</button>
                            <a href="/profile" class="btn btn-secondary w-100 mt-2">Отмена</a>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

FORGOT_PASSWORD_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Восстановление пароля</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <div class="container mt-5">
        <div class="row justify-content-center">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header bg-warning">
                        <h3>Восстановление пароля</h3>
                    </div>
                    <div class="card-body">
                        <form method="post">
                            <div class="mb-3">
                                <label>Введите ваш email</label>
                                <input type="email" name="email" class="form-control" required>
                            </div>
                            <button type="submit" class="btn btn-warning w-100">Отправить ссылку</button>
                            <a href="/login" class="btn btn-secondary w-100 mt-2">Назад ко входу</a>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

PROJECTS_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Мои проекты</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="/projects">ProjectManager</a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="/profile">Профиль</a>
                <a class="nav-link" href="/logout">Выйти</a>
            </div>
        </div>
    </nav>
    <div class="container mt-4">
        <div class="row">
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header bg-success text-white">
                        <h4>Создать проект</h4>
                    </div>
                    <div class="card-body">
                        <form method="post" action="/projects/create">
                            <div class="mb-3">
                                <label>Название</label>
                                <input type="text" name="name" class="form-control" required>
                            </div>
                            <div class="mb-3">
                                <label>Описание</label>
                                <textarea name="description" class="form-control" rows="3"></textarea>
                            </div>
                            <div class="mb-3">
                                <label>Статус</label>
                                <select name="status" class="form-select">
                                    <option value="active">Активный</option>
                                    <option value="completed">Завершен</option>
                                    <option value="archived">Архив</option>
                                </select>
                            </div>
                            <button type="submit" class="btn btn-success w-100">Создать</button>
                        </form>
                    </div>
                </div>
            </div>
            <div class="col-md-8">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h4>Мои проекты</h4>
                    </div>
                    <div class="card-body">
                        <!-- Статистика -->
                        <div class="row mb-3 text-center">
                            <div class="col-3">
                                <div class="border rounded p-2">
                                    <h5 class="text-primary">{total_count}</h5>
                                    <small>Всего</small>
                                </div>
                            </div>
                            <div class="col-3">
                                <div class="border rounded p-2">
                                    <h5 class="text-success">{active_count}</h5>
                                    <small>Активные</small>
                                </div>
                            </div>
                            <div class="col-3">
                                <div class="border rounded p-2">
                                    <h5 class="text-secondary">{completed_count}</h5>
                                    <small>Завершены</small>
                                </div>
                            </div>
                            <div class="col-3">
                                <div class="border rounded p-2">
                                    <h5 class="text-danger">{archived_count}</h5>
                                    <small>Архив</small>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Поиск и фильтры -->
                        <div class="row mb-3">
                            <div class="col-6">
                                <form method="get" action="/projects">
                                    <div class="input-group">
                                        <input type="text" name="search" class="form-control" placeholder="Поиск..." value="{search_query}">
                                        <button type="submit" class="btn btn-primary">Найти</button>
                                        {search_clear_button}
                                    </div>
                                </form>
                            </div>
                            <div class="col-6">
                                <div class="btn-group w-100">
                                    <a href="/projects?status=all" class="btn btn-outline-secondary btn-sm">Все</a>
                                    <a href="/projects?status=active" class="btn btn-outline-success btn-sm">Активные</a>
                                    <a href="/projects?status=completed" class="btn btn-outline-secondary btn-sm">Завершенные</a>
                                    <a href="/projects?status=archived" class="btn btn-outline-danger btn-sm">Архив</a>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Список проектов -->
                        <div class="row">
                            {projects_html}
                        </div>
                        {empty_message}
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
    return HTMLResponse(content=PROFILE_PAGE.format(
        username=user.username, full_name=user.full_name or "", email=user.email, role=user.role, created_at=user.created_at
    ))

@app.get("/profile/edit")
async def edit_profile_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    return HTMLResponse(content=EDIT_PROFILE_PAGE.format(username=user.username, email=user.email, full_name=user.full_name or ""))

@app.post("/profile/edit")
async def edit_profile(request: Request, email: str = Form(...), username: str = Form(...), full_name: str = Form(""), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    user.email = email
    user.username = username
    user.full_name = full_name
    user.updated_at = str(datetime.now())
    db.commit()
    return RedirectResponse("/profile", status_code=303)

@app.get("/profile/change-password")
async def change_password_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    return HTMLResponse(content=CHANGE_PASSWORD_PAGE)

@app.post("/profile/change-password")
async def change_password(request: Request, old_password: str = Form(...), new_password: str = Form(...), confirm_password: str = Form(...), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    if new_password != confirm_password:
        return HTMLResponse(content="<h3>Пароли не совпадают! <a href='/profile/change-password'>Назад</a></h3>")
    if not verify_password(old_password, user.hashed_password):
        return HTMLResponse(content="<h3>Неверный текущий пароль! <a href='/profile/change-password'>Назад</a></h3>")
    user.hashed_password = hash_password(new_password)
    db.commit()
    return HTMLResponse(content="<h3>Пароль успешно изменен! <a href='/profile'>В профиль</a></h3>")

@app.get("/forgot-password")
async def forgot_password_page():
    return HTMLResponse(content=FORGOT_PASSWORD_PAGE)

@app.post("/forgot-password")
async def forgot_password(email: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if user:
        token = generate_reset_token()
        user.reset_token = token
        user.reset_token_expires = str(datetime.now() + timedelta(hours=1))
        db.commit()
        reset_link = f"/reset-password?token={token}"
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head><title>Сброс пароля</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet"></head>
        <body class="bg-light">
            <div class="container mt-5">
                <div class="card"><div class="card-header bg-success"><h3>Ссылка для сброса</h3></div>
                <div class="card-body"><a href="{reset_link}" class="btn btn-primary">Сбросить пароль</a></div></div>
            </div>
        </body>
        </html>
        """)
    return HTMLResponse(content="<h3>Email не найден! <a href='/forgot-password'>Назад</a></h3>")

@app.get("/reset-password")
async def reset_password_page(token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.reset_token == token).first()
    if not user:
        return HTMLResponse(content="<h3>Неверная ссылка! <a href='/forgot-password'>Попробовать снова</a></h3>")
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head><title>Сброс пароля</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet"></head>
    <body class="bg-light">
        <div class="container mt-5">
            <div class="card"><div class="card-header bg-info"><h3>Новый пароль</h3></div>
            <div class="card-body">
                <form method="post" action="/reset-password">
                    <input type="hidden" name="token" value="{token}">
                    <input type="password" name="new_password" class="form-control mb-2" placeholder="Новый пароль" required>
                    <input type="password" name="confirm_password" class="form-control mb-2" placeholder="Подтверждение" required>
                    <button type="submit" class="btn btn-info w-100">Сохранить</button>
                </form>
            </div></div>
        </div>
    </body>
    </html>
    """)

@app.post("/reset-password")
async def reset_password(token: str = Form(...), new_password: str = Form(...), confirm_password: str = Form(...), db: Session = Depends(get_db)):
    if new_password != confirm_password:
        return HTMLResponse(content=f"<h3>Пароли не совпадают! <a href='/reset-password?token={token}'>Назад</a></h3>")
    user = db.query(User).filter(User.reset_token == token).first()
    if not user:
        return HTMLResponse(content="<h3>Неверная ссылка! <a href='/forgot-password'>Попробовать снова</a></h3>")
    user.hashed_password = hash_password(new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()
    return HTMLResponse(content="<h3>Пароль изменен! <a href='/login'>Войти</a></h3>")

# ==================== ПРОЕКТЫ ====================

@app.get("/projects")
async def projects_list(
    request: Request, 
    search: str = "",
    status: str = "all",
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    
    query = db.query(Project).filter(Project.owner_id == user.id)
    
    if status != "all":
        query = query.filter(Project.status == status)
    
    if search:
        query = query.filter(
            or_(
                Project.name.contains(search),
                Project.description.contains(search)
            )
        )
    
    projects = query.order_by(Project.created_at.desc()).all()
    
    total_count = db.query(Project).filter(Project.owner_id == user.id).count()
    active_count = db.query(Project).filter(Project.owner_id == user.id, Project.status == "active").count()
    completed_count = db.query(Project).filter(Project.owner_id == user.id, Project.status == "completed").count()
    archived_count = db.query(Project).filter(Project.owner_id == user.id, Project.status == "archived").count()
    
    if projects:
        projects_html = ""
        for p in projects:
            status_badge = ""
            if p.status == "active":
                status_badge = '<span class="badge bg-success">Активный</span>'
            elif p.status == "completed":
                status_badge = '<span class="badge bg-secondary">Завершен</span>'
            else:
                status_badge = '<span class="badge bg-danger">Архив</span>'
            
            projects_html += f"""
            <div class="col-md-4 mb-3">
                <div class="card h-100">
                    <div class="card-body">
                        <div class="d-flex justify-content-between">
                            <h5>{p.name}</h5>
                            {status_badge}
                        </div>
                        <p class="text-muted">{p.description[:100] if p.description else "Нет описания"}</p>
                        <small class="text-muted">Создан: {p.created_at.split()[0] if p.created_at else "Недавно"}</small>
                    </div>
                </div>
            </div>
            """
        empty_message = ""
    else:
        projects_html = ""
        empty_message = '<div class="col-12"><div class="alert alert-info">Нет проектов. Создайте первый!</div></div>'
    
    search_clear_button = ""
    if search:
        search_clear_button = f'<a href="/projects?status={status}" class="btn btn-outline-secondary">Очистить</a>'
    else:
        search_clear_button = ""
    
    return HTMLResponse(content=PROJECTS_PAGE.format(
        total_count=total_count,
        active_count=active_count,
        completed_count=completed_count,
        archived_count=archived_count,
        projects_html=projects_html,
        empty_message=empty_message,
        search_query=search,
        search_clear_button=search_clear_button
    ))

@app.post("/projects/create")
async def create_project(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    status: str = Form("active"),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    
    new_project = Project(name=name, description=description, status=status, owner_id=user.id)
    db.add(new_project)
    db.commit()
    return RedirectResponse("/projects", status_code=303)

@app.get("/logout")
async def logout():
    response = RedirectResponse("/login")
    response.delete_cookie("access_token")
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)