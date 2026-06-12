from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text
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
    owner_id = Column(Integer)
    created_at = Column(String, default=str(datetime.now()))

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
<body>
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
                        {projects_html}
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
        <head><title>Ссылка для сброса</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet"></head>
        <body class="bg-light">
            <div class="container mt-5">
                <div class="row justify-content-center">
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header bg-success text-white"><h3>Ссылка для сброса пароля</h3></div>
                            <div class="card-body">
                                <a href="{reset_link}" class="btn btn-primary">Сбросить пароль</a>
                            </div>
                        </div>
                    </div>
                </div>
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
            <div class="row justify-content-center">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header bg-info text-white"><h3>Сброс пароля</h3></div>
                        <div class="card-body">
                            <form method="post" action="/reset-password">
                                <input type="hidden" name="token" value="{token}">
                                <div class="mb-3"><label>Новый пароль</label><input type="password" name="new_password" class="form-control" required></div>
                                <div class="mb-3"><label>Подтверждение</label><input type="password" name="confirm_password" class="form-control" required></div>
                                <button type="submit" class="btn btn-info w-100">Сохранить</button>
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
        return HTMLResponse(content="<h3>Пароли не совпадают! <a href='/reset-password?token={token}'>Назад</a></h3>")
    user = db.query(User).filter(User.reset_token == token).first()
    if not user:
        return HTMLResponse(content="<h3>Неверная ссылка! <a href='/forgot-password'>Попробовать снова</a></h3>")
    user.hashed_password = hash_password(new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()
    return HTMLResponse(content="<h3>Пароль успешно изменен! <a href='/login'>Войти</a></h3>")

@app.get("/projects")
async def projects_list(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    projects = db.query(Project).filter(Project.owner_id == user.id).all()
    if projects:
        projects_html = '<div class="list-group">'
        for p in projects:
            projects_html += f'<div class="list-group-item"><h5>{p.name}</h5><p>{p.description or ""}</p><small>{p.created_at}</small></div>'
        projects_html += '</div>'
    else:
        projects_html = '<p>У вас пока нет проектов</p>'
    return HTMLResponse(content=PROJECTS_PAGE.format(username=user.username, projects_html=projects_html))

@app.post("/projects/create")
async def create_project(request: Request, name: str = Form(...), description: str = Form(""), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    new_project = Project(name=name, description=description, owner_id=user.id)
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