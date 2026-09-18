# LOCAL RUN — Gate 1 Spike

## المتطلبات
- Python 3.12+
- pip

## تشغيل سريع بـSQLite للتجريب فقط

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py makemigrations core
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

ثم:
- الموقع: http://127.0.0.1:8000/
- Admin: http://127.0.0.1:8000/admin/
- Health: http://127.0.0.1:8000/health/

## PostgreSQL

انسخ قيم البيئة من `.env.example` إلى بيئة التشغيل. لا ترفع كلمات المرور إلى GitHub.

ثم:
```bash
python manage.py migrate
python manage.py runserver
```

## الاختبارات

```bash
python manage.py test -v 2
python manage.py check
```

## ملاحظة
SQLite هنا fallback للتطوير والـCI فقط. Production المستهدفة PostgreSQL.
