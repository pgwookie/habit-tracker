# Habit Tracker (Django)

Учебный проект: трекер привычек на Django.

## Функции (на текущий момент)
- Регистрация / вход / выход
- Личный кабинет (username/email/дата регистрации)
- Редактирование профиля: full_name, bio, timezone (селект), язык по умолчанию
- Локализация RU/EN + переключатель языка в navbar


## Требования
- Python 3.9+
- (опционально) GNU gettext tools (msgfmt/msguniq) для переводов

## Установка и запуск (Windows)
1) Создать и активировать venv:
python -m venv .venv
.\.venv\Scripts\Activate.ps1

Установить зависимости:

pip install -r requirements.txt

Создать .env по примеру:

скопируй .env.example → .env

заполни SECRET_KEY

Применить миграции и запустить сервер:

.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver

Открыть:

http://127.0.0.1:8000/accounts/login/

http://127.0.0.1:8000/accounts/profile/