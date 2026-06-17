markdown
# Инструкция по установке и запуску
## Онлайн-платформа управления проектами

---

## 1. Системные требования

### Минимальные требования:
| Компонент | Требование |
|-----------|------------|
| **Операционная система** | Windows 10/11, macOS 10.15+, Linux (Ubuntu 20.04+) |
| **Python** | Версия 3.8 или выше |
| **Git** | Для клонирования репозитория (опционально) |
| **Оперативная память** | 512 МБ (рекомендуется 1 ГБ) |
| **Место на диске** | 100 МБ |
| **Браузер** | Chrome, Firefox, Edge, Safari (последние версии) |

### Проверка версии Python:
```bash
python --version
# или
python3 --version
Если Python не установлен, скачайте его с официального сайта:

Windows/macOS: https://www.python.org/downloads/

Linux: sudo apt install python3 python3-pip (Ubuntu/Debian)

2. Способы скачивания проекта
Способ 1: Клонирование через Git (рекомендуется)
bash
# Клонируем репозиторий
git clone https://github.com/Azim-cloud/project_platform.git

# Переходим в папку проекта
cd project_platform
Если Git не установлен:

Windows: https://git-scm.com/download/win

macOS: brew install git

Linux: sudo apt install git

Способ 2: Скачать ZIP-архив (без Git)
Перейдите на страницу репозитория:
https://github.com/Azim-cloud/project_platform

Нажмите зелёную кнопку "Code"

В выпадающем меню выберите "Download ZIP"

Распакуйте архив в удобную папку (например, C:\Projects\)

Откройте терминал и перейдите в распакованную папку:

bash
cd C:\Projects\project_platform-main
Способ 3: Через GitHub Desktop (визуальный интерфейс)
Скачайте GitHub Desktop: https://desktop.github.com/

Войдите в свой аккаунт GitHub

Нажмите "Clone a repository"

Выберите Azim-cloud/project_platform

Укажите папку для сохранения

Нажмите "Clone"

3. Создание виртуального окружения
Виртуальное окружение изолирует зависимости проекта от системных.

Windows (Git Bash)
bash
# Создаём виртуальное окружение
python -m venv venv

# Активируем
source venv/Scripts/activate
Windows (CMD / PowerShell)
cmd
python -m venv venv
venv\Scripts\activate
Windows (PowerShell с ограничениями)
Если PowerShell выдаёт ошибку о запрете выполнения скриптов:

powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
venv\Scripts\Activate.ps1
macOS / Linux
bash
# Создаём виртуальное окружение
python3 -m venv venv

# Активируем
source venv/bin/activate
Debian/Ubuntu (если venv не установлен)
bash
sudo apt install python3-venv
python3 -m venv venv
source venv/bin/activate
4. Установка зависимостей
Вариант 1: Через requirements.txt (рекомендуется)
bash
pip install -r requirements.txt
Вариант 2: Установка вручную
bash
pip install fastapi uvicorn sqlalchemy python-jose[cryptography] passlib[bcrypt] python-multipart
Вариант 3: Установка с указанием версий
bash
pip install fastapi==0.104.1 uvicorn==0.24.0 sqlalchemy==2.0.23 python-jose[cryptography]==3.3.0 passlib[bcrypt]==1.7.4 python-multipart==0.0.6
Проверка установленных пакетов:
bash
pip list
5. Настройка базы данных
База данных создаётся автоматически при первом запуске.

Ручное создание (опционально):
bash
python -c "from app.user_system import Base, engine; Base.metadata.create_all(engine)"
Сброс базы данных (если нужно начать заново):
bash
rm projects.db  # Linux/macOS
del projects.db # Windows
6. Запуск приложения
Запуск стабильной версии:
bash
python app/user_system.py
Запуск оптимизированной версии (рекомендуется):
bash
python app/main_optimized.py
Запуск с указанием порта (если 8000 занят):
bash
python app/user_system.py --port 8001
Запуск с доступом из локальной сети:
bash
# В файле user_system.py замените host="127.0.0.1" на host="0.0.0.0"
uvicorn.run(app, host="0.0.0.0", port=8000)
7. Доступ к приложению
После запуска в терминале появится сообщение:

text
INFO:     Started server process [xxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
Откройте браузер и перейдите по адресу:
Для доступа	Адрес
Локальный компьютер	http://localhost:8000
Тот же компьютер	http://127.0.0.1:8000
С другого устройства в сети	http://[IP-адрес_компьютера]:8000
8. Вход в систему
Администратор (создаётся автоматически при первом запуске):
Поле	Значение
Имя пользователя	admin
Пароль	admin123
Обычный пользователь:
На странице входа нажмите "Зарегистрироваться"

Заполните форму:

Email (например, user@example.com)

Имя пользователя

Полное имя

Пароль (минимум 6 символов)

Нажмите "Зарегистрироваться"

Войдите с созданными данными

9. Остановка сервера
Нажмите Ctrl + C в терминале, где запущен сервер

Подождите, пока сервер завершит работу

10. Возможные проблемы и их решение
Проблема 1: ModuleNotFoundError: No module named 'fastapi'
Причина: Не установлены зависимости.

Решение:

bash
pip install fastapi uvicorn sqlalchemy python-jose[cryptography] passlib[bcrypt] python-multipart
Проблема 2: sqlite3.OperationalError: no such table
Причина: База данных повреждена или отсутствует.

Решение:

bash
rm projects.db  # Linux/macOS
del projects.db # Windows
python app/user_system.py
Проблема 3: Address already in use (порт 8000 занят)
Причина: Другое приложение использует порт 8000.

Решение 1 — использовать другой порт:

bash
python app/user_system.py --port 8001
Решение 2 — найти и закрыть процесс:

bash
# Windows
netstat -ano | findstr :8000
taskkill /PID [PID] /F

# Linux/macOS
lsof -i :8000
kill -9 [PID]
Проблема 4: Permission denied при активации venv (Linux/macOS)
Решение:

bash
chmod +x venv/bin/activate
source venv/bin/activate
Проблема 5: Ошибка при установке python-jose[cryptography]
Решение:

bash
# Установите отдельно
pip install python-jose cryptography
Проблема 6: Не открывается страница с другого устройства
Решение:

Запустите сервер с host="0.0.0.0"

Проверьте IP-адрес компьютера: ipconfig (Windows) или ifconfig (Linux/macOS)

Разрешите порт 8000 в брандмауэре Windows

Проблема 7: Ошибка DetachedInstanceError
Решение: Используйте стабильную версию user_system.py вместо main_optimized.py.

bash
python app/user_system.py
11. Структура проекта после установки
text
project_platform/
├── app/
│   ├── __init__.py              # Инициализация пакета
│   ├── user_system.py           # Основное приложение (стабильная версия)
│   ├── main_optimized.py        # Оптимизированная версия
│   ├── static/                  # Статические файлы
│   └── templates/               # HTML шаблоны
├── docs/
│   ├── documentation/           # Документация
│   │   ├── USER_GUIDE.md        # Руководство пользователя
│   │   ├── INSTALLATION.md      # Инструкция по установке
│   │   ├── PROJECT_STRUCTURE.md # Структура проекта
│   │   └── TECH_DOCS.md         # Техническая документация
│   └── day1/ ... day10/         # Скриншоты по дням
├── projects.db                  # База данных SQLite
├── venv/                        # Виртуальное окружение
└── requirements.txt             # Зависимости проекта
12. Проверка работоспособности
После запуска проверьте следующие пункты:

№	Проверка	Ожидаемый результат
1	Открыть /register	Страница регистрации
2	Зарегистрировать пользователя	Перенаправление на /login
3	Войти с созданными данными	Перенаправление на /projects
4	Создать проект	Проект появляется в списке
5	Перейти в /tasks	Страница задач открывается
6	Создать задачу	Задача появляется в списке
7	Открыть задачу	Видна полная информация
8	Добавить комментарий	Комментарий появляется
9	Перейти в /profile	Данные пользователя отображаются
10	Войти как admin / admin123	Доступ к админ-панели
13. Обновление проекта
Если вы уже установили проект и хотите обновить его до последней версии:

bash
# Сохраните изменения (если есть)
git stash

# Скачайте последние изменения
git pull

# Обновите зависимости
pip install -r requirements.txt

# Перезапустите приложение
python app/user_system.py
14. Удаление проекта
Если вы хотите полностью удалить проект:

bash
# Удалите папку проекта
rm -rf project_platform  # Linux/macOS
rmdir /s project_platform # Windows
15. Контакты и поддержка
Автор: Azim-cloud

GitHub репозиторий: https://github.com/Azim-cloud/project_platform

Email: [указать email, если есть]

Если вы нашли ошибку или у вас есть предложения по улучшению, создайте Issue на GitHub или свяжитесь с автором.

16. Лицензия
Проект распространяется под лицензией MIT.