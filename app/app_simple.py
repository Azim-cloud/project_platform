from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from jose import jwt
from datetime import datetime, timedelta
import hashlib
import secrets

# База данных
DATABASE_URL = "sqlite:///./projects.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Модель пользователя (без full_name для простоты)
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="user")
    is_active = Column(Boolean, default=True)
    created_at = Column(String, default=str(datetime.now()))

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True)
    name = Column(String, index=True)
    description = Column(Text, default="")
    owner_id = Column(Integer)
    created_at = Column(String, default=str(datetime.now()))

Base.metadata.create_all(bind=engine)

app = FastAPI()
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"

# Простое хэширование пароля (без bcrypt)
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    return salt + ":" + hashlib.sha256((salt + password).encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    salt, hash_value = hashed_password.split(":")
    return hash_value == hashlib.sha256((salt + plain_password).encode()).hexdigest()

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

# HTML страницы
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
                    <div class="card-header">
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
                            <button type="submit" class="btn btn-primary">Войти</button>
                            <a href="/register" class="btn btn-link">Нет аккаунта?</a>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

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
                    <div class="card-header">
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
                                <label>Пароль</label>
                                <input type="password" name="password" class="form-control" required>
                            </div>
                            <button type="submit" class="btn btn-primary">Зарегистрироваться</button>
                            <a href="/login" class="btn btn-link">Уже есть аккаунт?</a>
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
                <span class="nav-link text-light">Привет, {username}</span>
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
                            <button type="submit" class="btn btn-success">Создать</button>
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
                <span class="nav-link text-light">Привет, {username}</span>
                <a class="nav-link" href="/profile">Профиль</a>
                <a class="nav-link" href="/logout">Выйти</a>
            </div>
        </div>
    </nav>
    <div class="container mt-4">
        <div class="row justify-content-center">
            <div class="col-md-8">
                <div class="card">
                    <div class="card-header bg-info text-white">
                        <h4>Личный кабинет</h4>
                    </div>
                    <div class="card-body">
                        <table class="table">
                            <tr><td><strong>Имя пользователя:</strong></td><td>{username}</td></tr>
                            <tr><td><strong>Email:</strong></td><td>{email}</td></tr>
                            <tr><td><strong>Роль:</strong></td><td>{role}</td></tr>
                            <tr><td><strong>Дата регистрации:</strong></td><td>{created_at}</td></tr>
                        </table>
                        <a href="/projects" class="btn btn-primary">← Назад к проектам</a>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

# Маршруты
@app.get("/")
async def home():
    return RedirectResponse("/login")

@app.get("/login")
async def login_page():
    return HTMLResponse(content=LOGIN_PAGE)

@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return RedirectResponse("/login?error=invalid", status_code=303)
    token = create_access_token(data={"sub": user.username})
    response = RedirectResponse("/projects", status_code=303)
    response.set_cookie(key="access_token", value=token, httponly=True)
    return response

@app.get("/register")
async def register_page():
    return HTMLResponse(content=REGISTER_PAGE)

@app.post("/register")
async def register(email: str = Form(...), username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    existing = db.query(User).filter((User.email == email) | (User.username == username)).first()
    if existing:
        return HTMLResponse(content="<h3>Пользователь уже существует! <a href='/register'>Назад</a></h3>", status_code=400)
    new_user = User(email=email, username=username, hashed_password=hash_password(password))
    db.add(new_user)
    db.commit()
    return RedirectResponse(url="/login", status_code=303)

@app.get("/projects")
async def projects_list(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    
    projects = db.query(Project).filter(Project.owner_id == user.id).all()
    
    if projects:
        projects_html = '<div class="list-group">'
        for p in projects:
            projects_html += f'''
                <div class="list-group-item">
                    <h5>{p.name}</h5>
                    <p>{p.description or "Нет описания"}</p>
                    <small>Создан: {p.created_at}</small>
                </div>
            '''
        projects_html += '</div>'
    else:
        projects_html = '<p>У вас пока нет проектов. Создайте первый проект!</p>'
    
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

@app.get("/profile")
async def profile(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")
    
    return HTMLResponse(content=PROFILE_PAGE.format(
        username=user.username,
        email=user.email,
        role=user.role,
        created_at=user.created_at
    ))

@app.get("/logout")
async def logout():
    response = RedirectResponse("/login")
    response.delete_cookie("access_token")
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)