# GATE 1 — TECHNICAL SPIKE

## الهدف

اختيار أبسط Stack إنتاجي يحقق: الحسابات، قاعدة بيانات مركزية، النموذج الشجري، المواصفات الديناميكية، RTL/mobile، الصلاحيات، versioning، وسهولة التطوير.

## البدائل التي تمت مراجعتها

### A. Django + PostgreSQL + server-rendered templates
**نقاط القوة**
- Authentication وصلاحيات وموقع Admin مدمجة.
- ORM وMigrations وForms وCSRF/Sessions ضمن إطار واحد.
- PostgreSQL مدعوم رسميًا.
- مناسب لتطبيق إداري متعدد المستخدمين دون الحاجة إلى SPA.
- يمكن إضافة HTMX لاحقًا للتحسين التدريجي دون تغيير المعمارية.

**التكلفة**
- نحتاج hosting لخادم Python + PostgreSQL.
- Admin Builder الميداني المخصص سيبنى فوق Django؛ Django Admin وحده ليس واجهة المفتش النهائية.

### B. Supabase + browser client
**نقاط القوة**
- PostgreSQL + Auth + API جاهزة.
- سرعة بدء عالية.
- RLS تسمح بصلاحيات دقيقة داخل قاعدة البيانات.

**المخاطر**
- RLS/grants تصبح جزءًا أساسيًا من نموذج الأمن ويجب اختبارها بدقة.
- يتطلب إدارة جيدة لحدود client/server وعدم كشف secret/service keys.
- Builder المعقد سيظل يحتاج Frontend أكبر.

### C. FastAPI + SQLAlchemy + PostgreSQL
**نقاط القوة**
- API واضح وتحكم كامل.
- typing/validation قوي.

**التكلفة**
- Authentication وAdmin وForms/CSRF/permissions تحتاج تركيبًا أكبر من Django.
- لا تحقق هدف "الأبسط" لهذا المنتج في V1.

### D. Frappe / generic low-code
يوفر كثيرًا جاهزًا لكنه ينقلنا مبكرًا إلى منصة أوسع وقيود تشغيلية أكبر من حاجة V1.

## نتيجة Spike

**الاختيار الموصى به: Django 5.2 LTS + PostgreSQL + Django Templates.**

HTMX اختياري لاحقًا، وليس dependency في Gate 1.

سبب الاختيار: أقل عدد من المكونات مع أعلى قدر من Auth/Admin/ORM/Migrations/Security مدمج، مع الاحتفاظ بإمكانية بناء UI ميدانية بسيطة ومخصصة.

## ما يثبته Prototype الحالي

- login route وحماية dashboard؛
- أدوار Admin/Inspector في النموذج؛
- اتصال PostgreSQL عبر environment مع SQLite فقط كـdev/test fallback؛
- Recursive StructureNode؛
- Dynamic SpecificationDefinition؛
- Checklist status contract؛
- MasterVersion؛
- Inspection pinned to MasterVersion؛
- historical snapshot؛
- Proposal pending moderation؛
- RTL responsive shell؛
- Django Admin كنقطة إدارة تقنية أولية.

## ما لا يثبته Gate 1

- Admin Builder النهائي؛
- كامل workflow المفتش؛
- autosave production؛
- proposal resolution UI؛
- publish engine الكامل؛
- production hosting.

هذه تخص البوابات التالية.
