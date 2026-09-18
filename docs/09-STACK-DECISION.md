# STACK DECISION — ADR-001

## Status
**PROPOSED FOR ACCEPTANCE**

## Decision
اعتماد:
- Python
- Django 5.2 LTS
- PostgreSQL في Production
- Django Templates للواجهة
- CSS/JavaScript محدود
- HTMX لاحقًا فقط عندما يختصر تفاعلًا محددًا
- Django Admin للإدارة التقنية المبكرة، مع Admin Builder مخصص في Gate 3

## لماذا ليس SPA؟
الموقع إداري/ميداني، والنواة CRUD + forms + tree navigation. SPA ستضيف build/tooling/state/API complexity قبل وجود حاجة مثبتة.

## لماذا Django؟
الإطار يوفر Authentication وAuthorization وAdmin وORM وMigrations وCSRF/Sessions وtemplating واختبارات ضمن stack واحد.

## قاعدة البيانات
PostgreSQL Production من اليوم الأول في التصميم. SQLite مسموح فقط للتطوير المحلي والـCI السريع، وليس مرجعًا لميزات Production.

## Security
- server-side authorization؛
- CSRF middleware؛
- secure cookies في Production؛
- لا secrets داخل المستودع؛
- HTTPS في Production؛
- least privilege DB credentials؛
- backup policy قبل Pilot.

## Version policy
Pin إلى سلسلة Django 5.2 LTS وتحديث patch releases أمنيًا ضمن 5.2.x حتى قرار ترقية مدروس.

## Exit criteria
بعد قبول هذا ADR، Gate 2 تبدأ ببناء schema/migrations النهائية والـAuth/roles الأساسية، لا بإضافة Features جانبية.
