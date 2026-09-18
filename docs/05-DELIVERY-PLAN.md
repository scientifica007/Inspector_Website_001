# DELIVERY PLAN — v0.1

## Gate 0 — Foundation
**الحالة:** قيد المراجعة

المخرجات:
- Charter
- Domain model
- Architecture
- Admin/Inspector workflows
- Research notes
- Decision log
- Current state

شرط القبول:
- اتفاق على المفاهيم الأساسية قبل Implementation.

## Gate 1 — Technical Spike

الهدف:
اختيار أبسط Stack يحقق Authentication + central database + recursive model + RTL/mobile.

المخرجات:
- Prototype تقني صغير؛
- قرار Stack موثق؛
- schema أولي قابل للمهاجرة؛
- اختبار login وقراءة/كتابة سجل واحد؛
- قرار hosting/deployment أولي.

لا Feature development واسع في هذه البوابة.

## Gate 2 — Core Data & Authentication

- Admin / Inspector.
- Institutions.
- Inspections Draft/Completed.
- قاعدة صلاحيات.
- Autosave foundation.

## Gate 3 — Admin Builder

- Recursive tree.
- Node CRUD.
- Specification definitions.
- Checklist items.
- ordering.
- deactivate.
- Draft preview.

## Gate 4 — Inspector Field Workflow

- إنشاء/استكمال زيارة.
- Rendering ديناميكي.
- الحالات الخمس.
- specification values.
- item observations.
- node observations/recommendations.
- general observations/recommendations.
- Mobile RTL.

## Gate 5 — Proposals + Versioning

- local additions.
- proposal inbox.
- approve/edit/merge/reject.
- publish Master Version.
- inspection pinned to version.
- snapshot protections.

## Gate 6 — Export + Pilot

- JSON export.
- QA.
- Browser/mobile acceptance.
- اختبار مع بيانات تجريبية.
- Pilot ميداني محدود.

## Stop Rule

بعد Gate 6 نتوقف عن إضافة Features ونستخدم النظام فعليًا.

لا تبدأ:
- AI داخل الموقع؛
- الصور؛
- Offline Sync؛
- dashboards؛
- Word/PDF؛
- GPS؛
إلا إذا كشف الـPilot حاجة حقيقية ومحددة.

## Definition of Done لكل Gate

- الكود/الوثائق في Branch منفصل؛
- اختبارات مناسبة؛
- لا أسرار؛
- Readback؛
- تحديث CHANGELOG وCURRENT-STATE؛
- PR قابل للمراجعة؛
- لا Merge إلى main دون قبول صريح.
