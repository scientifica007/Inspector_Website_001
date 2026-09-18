# Inspector_Website_001

موقع ويب عربي RTL لدعم التفتيش الميداني، مع مرجع قابل للهندسة من طرف Admin دون تعديل الكود لكل تغير في الواقع.

## ما يعمل الآن

- حسابات Admin / Inspector.
- مؤسسات مع مراجعة الإضافات الميدانية.
- إنشاء زيارة وربطها بآخر Master Version منشورة.
- Snapshot مستقرة لكل زيارة.
- شجرة Recursive للمجالات والفروع.
- مواصفات ديناميكية: نص، نص طويل، عدد، تاريخ، نعم/لا، اختيار واحد ومتعدد.
- بنود تفتيش بالحالات: غير مفحوص / غير معني / مطابق / ملاحظة / غير مطابق.
- معاينات على مستوى البند والمجال والزيارة.
- توصيات على مستوى المجال والزيارة.
- Admin Builder لتشكيل المرجع.
- RTL وMobile-first.

## Stack
- Django 5.2 LTS
- PostgreSQL في Production
- Django Templates
- HTMX مؤجل حتى تظهر حاجة محددة

## الحالة

Foundation + Gate 1 + Gate 2 + Gate 3 مدمجة في `main`.
Gate 4 — Inspector Field Workflow اجتازت CI بـ **33/33** اختبارًا وهي جاهزة للدمج.
بعدها: Gate 5 — Proposals + Versioning.

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
- [Gate 4 Result](docs/13-GATE-4-RESULT.md)
- [Current State](CURRENT-STATE.json)
- [Changelog](CHANGELOG.md)
