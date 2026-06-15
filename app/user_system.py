from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text, or_, ForeignKey
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

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True)
    name = Column(String, index=True)
    description = Column(Text, default="")
    status = Column(String, default="active")
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(String, default=str(datetime.now()))
    updated_at = Column(String, default=str(datetime.now()))
    owner = relationship("User", backref="projects")

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
    project = relationship("Project", backref="tasks")
    creator = relationship("User", foreign_keys=[created_by])
    assignee = relationship("User", foreign_keys=[assigned_to])

Base.metadata.create_all(bind=engine)

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
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="/projects"><i class="fas fa-tasks"></i> ProjectManager</a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="/projects"><i class="fas fa-folder"></i> Проекты</a>
                <a class="nav-link" href="/tasks"><i class="fas fa-check-square"></i> Мои задачи</a>
                <a class="nav-link active" href="/profile"><i class="fas fa-user"></i> Профиль</a>
                <a class="nav-link" href="/logout"><i class="fas fa-sign-out-alt"></i> Выйти</a>
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
                            <tr><td><strong>Имя пользователя:</strong>ERC20<td>{username}ERC20</tr>
                            <tr><td><strong>Полное имя:</strong>ERC20<td>{full_name}ERC20</tr>
                            <tr><td><strong>Email:</strong>ERC20<td>{email}ERC20</tr>
                            <tr><td><strong>Роль:</strong>ERC20<td>{role}ERC20</tr>
                            <tr><td><strong>Дата регистрации:</strong>ERC20<td>{created_at}ERC20</tr>
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
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
</head>
<body class="bg-light">
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="/projects"><i class="fas fa-tasks"></i> ProjectManager</a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="/projects"><i class="fas fa-folder"></i> Проекты</a>
                <a class="nav-link" href="/tasks"><i class="fas fa-check-square"></i> Мои задачи</a>
                <a class="nav-link" href="/profile"><i class="fas fa-user"></i> Профиль</a>
                <a class="nav-link" href="/logout"><i class="fas fa-sign-out-alt"></i> Выйти</a>
            </div>
        </div>
    </nav>
    <div class="container mt-4">
        <div class="row">
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header bg-success text-white">
                        <h4><i class="fas fa-plus"></i> Создать проект</h4>
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
                        <h4><i class="fas fa-folder-open"></i> Мои проекты</h4>
                    </div>
                    <div class="card-body">
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

TASKS_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Мои задачи</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
</head>
<body class="bg-light">
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="/projects">ProjectManager</a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="/projects">Проекты</a>
                <a class="nav-link active" href="/tasks">Мои задачи</a>
                <a class="nav-link" href="/profile">{username}</a>
                <a class="nav-link" href="/logout">Выйти</a>
            </div>
        </div>
    </nav>
    <div class="container mt-4">
        <div class="d-flex justify-content-between">
            <h1>Мои задачи</h1>
            <button class="btn btn-success" data-bs-toggle="modal" data-bs-target="#createTaskModal">Создать задачу</button>
        </div>
        
        <div class="card mt-3">
            <div class="card-body">
                <div class="row">
                    <div class="col-md-4">
                        <form method="get">
                            <div class="input-group">
                                <input type="text" name="search" class="form-control" value="{search_query}">
                                <button class="btn btn-primary">Поиск</button>
                                {search_clear_button}
                            </div>
                        </form>
                    </div>
                    <div class="col-md-8">
                        <div class="btn-group w-100">
                            <a href="/tasks?status=all" class="btn btn-outline-secondary">Все</a>
                            <a href="/tasks?status=todo" class="btn btn-outline-secondary">To Do</a>
                            <a href="/tasks?status=in_progress" class="btn btn-outline-primary">В работе</a>
                            <a href="/tasks?status=review" class="btn btn-outline-warning">На проверке</a>
                            <a href="/tasks?status=done" class="btn btn-outline-success">Выполнено</a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row mt-4">
            <div class="col-md-3">
                <div class="card bg-secondary text-white">
                    <div class="card-body">
                        <h3>{todo_count}</h3>
                        <p>To Do</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-primary text-white">
                    <div class="card-body">
                        <h3>{progress_count}</h3>
                        <p>В работе</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-warning text-dark">
                    <div class="card-body">
                        <h3>{review_count}</h3>
                        <p>На проверке</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-success text-white">
                    <div class="card-body">
                        <h3>{done_count}</h3>
                        <p>Выполнено</p>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row mt-4">
            {tasks_html}
        </div>
        {empty_message}
    </div>
    
    <div class="modal fade" id="createTaskModal">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header bg-success text-white">
                    <h5>Новая задача</h5>
                    <button class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <form method="post" action="/tasks/create">
                    <div class="modal-body">
                        <input type="text" name="title" class="form-control mb-2" placeholder="Название" required>
                        <textarea name="description" class="form-control mb-2" placeholder="Описание"></textarea>
                        <select name="project_id" class="form-select mb-2" required>
                            <option value="">Выберите проект</option>
                            {projects_options}
                        </select>
                        <select name="status" class="form-select mb-2">
                            <option value="todo">To Do</option>
                            <option value="in_progress">В работе</option>
                            <option value="review">На проверке</option>
                            <option value="done">Выполнено</option>
                        </select>
                        <select name="priority" class="form-select">
                            <option value="low">Низкий</option>
                            <option value="medium">Средний</option>
                            <option value="high">Высокий</option>
                            <option value="urgent">Срочный</option>
                        </select>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                        <button class="btn btn-success">Создать</button>
                    </div>
                </form>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
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
        return HTMLResponse(content="<h3>Пароли не совпадают!</h3>")
    if not verify_password(old_password, user.hashed_password):
        return HTMLResponse(content="<h3>Неверный текущий пароль!</h3>")
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
        return HTMLResponse(content=f"<h3>Ссылка для сброса: <a href='/reset-password?token={token}'>Сбросить пароль</a></h3>")
    return HTMLResponse(content="<h3>Email не найден!</h3>")

@app.get("/reset-password")
async def reset_password_page(token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.reset_token == token).first()
    if not user:
        return HTMLResponse(content="<h3>Неверная ссылка!</h3>")
    return HTMLResponse(content=f"""
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
        return HTMLResponse(content="<h3>Пароли не совпадают!</h3>")
    user = db.query(User).filter(User.reset_token == token).first()
    if not user:
        return HTMLResponse(content="<h3>Неверная ссылка!</h3>")
    user.hashed_password = hash_password(new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()
    return HTMLResponse(content="<h3>Пароль изменен! <a href='/login'>Войти</a></h3>")

# ==================== ПРОЕКТЫ ====================

@app.get("/projects")
async def projects_list(request: Request, search: str = "", status: str = "all", db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    
    query = db.query(Project).filter(Project.owner_id == user.id)
    if status != "all":
        query = query.filter(Project.status == status)
    if search:
        query = query.filter(or_(Project.name.contains(search), Project.description.contains(search)))
    
    projects = query.order_by(Project.created_at.desc()).all()
    
    if projects:
        projects_html = ""
        for p in projects:
            status_badge = "bg-success" if p.status == "active" else "bg-secondary" if p.status == "completed" else "bg-danger"
            status_text = "Активный" if p.status == "active" else "Завершен" if p.status == "completed" else "Архив"
            projects_html += f"""
            <div class="col-md-6 mb-3">
                <div class="card">
                    <div class="card-body">
                        <h5>{p.name}</h5>
                        <p class="text-muted">{p.description[:100] if p.description else "Нет описания"}</p>
                        <span class="badge {status_badge}">{status_text}</span>
                        <div class="mt-2">
                            <a href="/projects/{p.id}/tasks" class="btn btn-sm btn-primary">Задачи</a>
                        </div>
                    </div>
                </div>
            </div>
            """
        empty_message = ""
    else:
        projects_html = ""
        empty_message = '<div class="col-12 alert alert-info">Нет проектов</div>'
    
    return HTMLResponse(content=PROJECTS_PAGE.format(
        projects_html=projects_html,
        empty_message=empty_message
    ))

@app.post("/projects/create")
async def create_project(request: Request, name: str = Form(...), description: str = Form(""), status: str = Form("active"), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    new_project = Project(name=name, description=description, status=status, owner_id=user.id)
    db.add(new_project)
    db.commit()
    return RedirectResponse("/projects", status_code=303)

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
    for t in tasks:
        tasks_html += f"""
        <div class="card mb-2">
            <div class="card-body">
                <h6>{t.title}</h6>
                <p>{t.description[:100] if t.description else ""}</p>
                <small>Статус: {t.status}</small>
            </div>
        </div>
        """
    
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Задачи проекта: {project.name}</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <nav class="navbar navbar-dark bg-dark">
            <div class="container">
                <a class="navbar-brand" href="/projects">ProjectManager</a>
            </div>
        </nav>
        <div class="container mt-4">
            <h2>Проект: {project.name}</h2>
            <p>{project.description}</p>
            <a href="/tasks" class="btn btn-primary mb-3">← Все задачи</a>
            <div class="card">
                <div class="card-header bg-primary text-white">
                    <h4>Задачи проекта</h4>
                </div>
                <div class="card-body">
                    {tasks_html if tasks_html else "Нет задач"}
                </div>
            </div>
        </div>
    </body>
    </html>
    """)

# ==================== ЗАДАЧИ ====================

@app.get("/tasks")
async def tasks_list(request: Request, search: str = "", status: str = "all", db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    
    query = db.query(Task).filter(Task.created_by == user.id)
    if status != "all":
        query = query.filter(Task.status == status)
    if search:
        query = query.filter(or_(Task.title.contains(search), Task.description.contains(search)))
    
    tasks = query.order_by(Task.created_at.desc()).all()
    
    todo_count = db.query(Task).filter(Task.created_by == user.id, Task.status == "todo").count()
    progress_count = db.query(Task).filter(Task.created_by == user.id, Task.status == "in_progress").count()
    review_count = db.query(Task).filter(Task.created_by == user.id, Task.status == "review").count()
    done_count = db.query(Task).filter(Task.created_by == user.id, Task.status == "done").count()
    
    projects = db.query(Project).filter(Project.owner_id == user.id).all()
    projects_options = ""
    for p in projects:
        projects_options += f'<option value="{p.id}">{p.name}</option>'
    
    if tasks:
        tasks_html = ""
        for t in tasks:
            priority_class = "priority-low" if t.priority == "low" else "priority-medium" if t.priority == "medium" else "priority-high" if t.priority == "high" else "priority-urgent"
            priority_text = "Низкий" if t.priority == "low" else "Средний" if t.priority == "medium" else "Высокий" if t.priority == "high" else "Срочный"
            status_badge = "bg-secondary" if t.status == "todo" else "bg-primary" if t.status == "in_progress" else "bg-warning" if t.status == "review" else "bg-success"
            status_text = "To Do" if t.status == "todo" else "В работе" if t.status == "in_progress" else "На проверке" if t.status == "review" else "Выполнено"
            project_name = t.project.name if t.project else "Без проекта"
            
            tasks_html += f"""
            <div class="col-md-4 mb-3">
                <div class="card task-card {priority_class} h-100">
                    <div class="card-body">
                        <div class="d-flex justify-content-between">
                            <h6>{t.title}</h6>
                            <span class="badge {status_badge}">{status_text}</span>
                        </div>
                        <p class="small text-muted">{t.description[:80] if t.description else "Нет описания"}</p>
                        <small><i class="fas fa-tag"></i> {priority_text}</small><br>
                        <small><i class="fas fa-folder"></i> {project_name}</small>
                        <div class="mt-2">
                            <a href="/tasks/{t.id}/edit" class="btn btn-sm btn-outline-primary">Ред.</a>
                            <a href="/tasks/{t.id}/delete" class="btn btn-sm btn-outline-danger" onclick="return confirm('Удалить?')">Уд.</a>
                            <div class="btn-group mt-1">
                                <a href="/tasks/{t.id}/status/todo" class="btn btn-sm btn-secondary">ToDo</a>
                                <a href="/tasks/{t.id}/status/in_progress" class="btn btn-sm btn-primary">В работу</a>
                                <a href="/tasks/{t.id}/status/review" class="btn btn-sm btn-warning">Проверка</a>
                                <a href="/tasks/{t.id}/status/done" class="btn btn-sm btn-success">Готово</a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            """
        empty_message = ""
    else:
        tasks_html = ""
        empty_message = '<div class="col-12 alert alert-info">Нет задач. Создайте первую задачу!</div>'
    
    search_clear_button = f'<a href="/tasks?status={status}" class="btn btn-outline-secondary">Очистить</a>' if search else ""
    
    return HTMLResponse(content=TASKS_PAGE.format(
        username=user.username,
        todo_count=todo_count,
        progress_count=progress_count,
        review_count=review_count,
        done_count=done_count,
        tasks_html=tasks_html,
        empty_message=empty_message,
        search_query=search,
        search_clear_button=search_clear_button,
        projects_options=projects_options
    ))

@app.post("/tasks/create")
async def create_task(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    status: str = Form("todo"),
    priority: str = Form("medium"),
    project_id: int = Form(...),
    db: Session = Depends(get_db)
):
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

@app.get("/tasks/{task_id}/edit")
async def edit_task_page(task_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    
    task = db.query(Task).filter(Task.id == task_id, Task.created_by == user.id).first()
    if not task:
        return HTMLResponse(content="<h3>Задача не найдена!</h3>")
    
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
    </head>
    <body class="bg-light">
        <div class="container mt-5">
            <div class="card">
                <div class="card-header bg-warning">
                    <h4>Редактирование задачи</h4>
                </div>
                <div class="card-body">
                    <form method="post" action="/tasks/{task_id}/edit">
                        <div class="mb-3">
                            <label>Название</label>
                            <input type="text" name="title" class="form-control" value="{task.title}" required>
                        </div>
                        <div class="mb-3">
                            <label>Описание</label>
                            <textarea name="description" class="form-control" rows="3">{task.description or ""}</textarea>
                        </div>
                        <div class="mb-3">
                            <label>Статус</label>
                            <select name="status" class="form-select">
                                <option value="todo" {'selected' if task.status == 'todo' else ''}>To Do</option>
                                <option value="in_progress" {'selected' if task.status == 'in_progress' else ''}>В работе</option>
                                <option value="review" {'selected' if task.status == 'review' else ''}>На проверке</option>
                                <option value="done" {'selected' if task.status == 'done' else ''}>Выполнено</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label>Приоритет</label>
                            <select name="priority" class="form-select">
                                <option value="low" {'selected' if task.priority == 'low' else ''}>Низкий</option>
                                <option value="medium" {'selected' if task.priority == 'medium' else ''}>Средний</option>
                                <option value="high" {'selected' if task.priority == 'high' else ''}>Высокий</option>
                                <option value="urgent" {'selected' if task.priority == 'urgent' else ''}>Срочный</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label>Проект</label>
                            <select name="project_id" class="form-select" required>
                                {projects_options}
                            </select>
                        </div>
                        <button type="submit" class="btn btn-warning w-100">Сохранить</button>
                        <a href="/tasks" class="btn btn-secondary w-100 mt-2">Отмена</a>
                    </form>
                </div>
            </div>
        </div>
    </body>
    </html>
    """)

@app.post("/tasks/{task_id}/edit")
async def edit_task(
    task_id: int,
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    status: str = Form("todo"),
    priority: str = Form("medium"),
    project_id: int = Form(...),
    db: Session = Depends(get_db)
):
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

@app.get("/logout")
async def logout():
    response = RedirectResponse("/login")
    response.delete_cookie("access_token")
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)