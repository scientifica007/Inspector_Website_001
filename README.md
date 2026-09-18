# Inspector_Website_001

موقع ويب عربي RTL لدعم التفتيش الميداني، مع مرجع قابل للهندسة من طرف Admin دون تعديل الكود لكل تغير في الواقع.

## النواة

- شجرة Recursive بلا مستويات ثابتة.
- مواصفات ديناميكية لكل عنصر.
- بنود تفتيش بخمس حالات: غير مفحوص / غير معني / مطابق / ملاحظة / غير مطابق.
- Draft / Publish / Version لحماية تاريخ الزيارات.
- إضافات المفتش محلية أولًا ثم Proposal للـAdmin.
- حسابات Admin / Inspector وحفظ مركزي.
- Mobile-first.

## Stack
- Django 5.2 LTS
- PostgreSQL في Production
- Django Templates
- HTMX مؤجل حتى تظهر حاجة محددة

## الحالة

Foundation + Gate 1 + Gate 2 مدمجة في `main`.
Gate 3 — Admin Builder اجتازت CI بـ **23/23** اختبارًا وهي جاهزة للدمج.
بعدها: Gate 4 — Inspector Field Workflow.

## وثائق المشروع
- [Project Charter](docs/00-PROJECT-CHARTER.md)
- [Domain Model](docs/01-DOMAIN-MODEL.md)
- [Architecture](docs/02-ARCHITECTURE.md)
- [Admin Builder](docs/03-ADMIN-BUILDER.md)
- [Inspector Workflow](docs/04-INSPECTOR-WORKFLOW.md)
- [Delivery Plan](docs/05-DELIVERY-PLAN.md)
- [Research Notes](docs/06-RESEARCH-NOTES.md)
- [Decision Log](docs/07-DECISIONS.md)
- [Gate 1 Technical Spike](docs/08-TECHNICAL-SPIKE.md)
- [Stack Decision](docs/09-STACK-DECISION.md)
- [Local Run](docs/10-LOCAL-RUN.md)
- [Gate 2 Result](docs/11-GATE-2-RESULT.md)
- [Gate 3 Result](docs/12-GATE-3-RESULT.md)
- [Current State](CURRENT-STATE.json)
- [Changelog](CHANGELOG.md)
