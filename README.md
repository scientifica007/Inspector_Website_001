# Inspector_Website_001

موقع ويب عربي RTL لدعم التفتيش الميداني، مع مرجع قابل للهندسة من طرف Admin دون تعديل الكود لكل تغير في الواقع.

## ما يعمل في V1 الحالية

- حسابات Admin / Inspector.
- إدارة المؤسسات ومراجعة الإضافات.
- Admin Builder لشجرة Recursive.
- مواصفات ديناميكية.
- بنود تفتيش بالحالات:
  - غير مفحوص
  - غير معني
  - مطابق
  - ملاحظة
  - غير مطابق
- Draft / Publish / Version.
- Stable logical IDs بين الإصدارات.
- زيارات مرتبطة بإصدار منشور مع Snapshot تاريخية.
- معاينات وتوصيات على مستوى البند والمجال والزيارة.
- إضافة فرع / مواصفة / بند من الميدان فورًا.
- Proposal Inbox: تعديل قبل الاعتماد / اعتماد / رفض / دمج مؤسسة.
- JSON Export منظم لاستخدامه لاحقًا خارج الموقع في إعداد التقرير.
- RTL وMobile-first.

## Stack

- Django 5.2 LTS
- PostgreSQL في Production
- Django Templates
- HTMX مؤجل حتى تظهر حاجة محددة

## Export

المخطط الحالي:

`inspection-export-v1`

التصدير يعتمد على Snapshot الزيارة لا على النص الحالي للـMaster، ويحافظ على العربية UTF-8.

## الحالة

Foundation + Gates 1–6 مدمجة في `main`.

Gate 6 التقنية اجتازت:
- migration drift check
- Django system check
- migrations
- **54/54** اختبارًا آليًا

Pilot candidate المثبت للاختبار البشري:

- branch: `pilot/v0.1-rc1`
- commit: `c752d61a9431eb5f7594c61447182a71acef69b2`

الحالة الصحيحة حاليًا:

**TECHNICAL-PASS — HUMAN ACCEPTANCE PENDING**

لا يُعلن `PILOT-READY` قبل إكمال `docs/15-PILOT-ACCEPTANCE.md` فعليًا على Desktop والهاتف.

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
- [Local Run / Pilot](docs/10-LOCAL-RUN.md)
- [Gate 2 Result](docs/11-GATE-2-RESULT.md)
- [Gate 3 Result](docs/12-GATE-3-RESULT.md)
- [Gate 4 Result](docs/13-GATE-4-RESULT.md)
- [Gate 5 Result](docs/14-GATE-5-RESULT.md)
- [Pilot Acceptance](docs/15-PILOT-ACCEPTANCE.md)
- [Export Schema](docs/16-EXPORT-SCHEMA.md)
- [Gate 6 Result](docs/17-GATE-6-RESULT.md)
- [Current State](CURRENT-STATE.json)
- [Changelog](CHANGELOG.md)
