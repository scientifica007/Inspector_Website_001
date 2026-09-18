# LOCAL RUN — V1 Pilot

## المتطلبات

- Python 3.12+
- pip
- Git

## 1. تجهيز البيئة المحلية

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
```

> الـMigrations جزء من المستودع. لا تشغّل `makemigrations` كخطوة تشغيل عادية.

## 2. إنشاء حساب Admin محلي

```bash
python manage.py createsuperuser
```

## 3. إنشاء بيانات Pilot تجريبية

الأمر `seed_demo` يعمل فقط عندما `DEBUG=True` ويرفض الكتابة إذا كانت قاعدة بيانات المشروع تحتوي أصلًا على MasterVersion أو Institution أو Inspection.

استخدم كلمة مرور محلية لا تكتبها في GitHub:

```bash
read -s PILOT_PASSWORD
export PILOT_PASSWORD
python manage.py seed_demo --username pilot-inspector
unset PILOT_PASSWORD
```

البيانات التي ينشئها الأمر خيالية فقط:
- مؤسسة تجريبية؛
- Master Version منشورة؛
- شجرة بها مجالات وفروع؛
- مواصفات ديناميكية؛
- بنود تفتيش؛
- زيارة مسودة للمفتش التجريبي.

## 4. تشغيل الموقع

```bash
python manage.py runserver
```

ثم افتح:

- الموقع: http://127.0.0.1:8000/
- Django Admin: http://127.0.0.1:8000/admin/
- Health: http://127.0.0.1:8000/health/

## 5. الاختبارات

```bash
python manage.py makemigrations --check --dry-run
python manage.py check
python manage.py test -v 2
```

## SQLite في Pilot محلي

SQLite مقبول للاختبار المحلي على جهاز واحد فقط.

### نسخة احتياطية

أوقف الخادم أولًا ثم:

```bash
cp db.sqlite3 "db.sqlite3.backup"
```

### استرجاع

أوقف الخادم، احتفظ بنسخة من الملف الحالي إن لزم، ثم استبدله بالنسخة الاحتياطية:

```bash
cp "db.sqlite3.backup" db.sqlite3
```

بعدها:

```bash
python manage.py check
python manage.py migrate
```

## PostgreSQL — اتجاه Production

Production المستهدف PostgreSQL. قيم الاتصال تؤخذ من متغيرات البيئة الموضحة في `.env.example`.

النسخ الاحتياطي يكون بأدوات PostgreSQL القياسية مثل:

```bash
pg_dump -Fc -h <host> -U <user> -d <database> -f backup.dump
```

والاسترجاع، إلى قاعدة مستهدفة مناسبة:

```bash
pg_restore -h <host> -U <user> -d <database> --clean --if-exists backup.dump
```

لا تضع كلمات المرور أو أسرار الاتصال داخل الأوامر المحفوظة في المستودع.

## قبل أي نشر متعدد المستخدمين

لا تعتبر تشغيل `runserver` أو SQLite نشرًا إنتاجيًا. راجع قائمة الأمان والقبول في:
- `docs/15-PILOT-ACCEPTANCE.md`
