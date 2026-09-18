# RESEARCH NOTES — 2026-09-18

> هذه الملاحظات للاستفادة من التجارب السابقة وليست متطلبات ملزمة للمشروع.

## KoboToolbox
أفكار مستفادة:
- Form Builder؛
- Question Library؛
- Groups/Repeat Groups؛
- Draft/Deploy؛
- إعادة استعمال المكونات؛
- مشاركة المكتبة.

مرجع:
- https://github.com/kobotoolbox/kpi
- https://support.kobotoolbox.org/question_library.html
- https://support.kobotoolbox.org/group_repeat.html

## ODK Central
أفكار مستفادة:
- Forms منشورة بإصدارات؛
- Submissions مرتبطة بتعريفات مستقرة؛
- الاحتفاظ بالإصدارات السابقة.

مرجع:
- https://github.com/getodk/central
- https://docs.getodk.org/central-forms/
- https://docs.getodk.org/central-api-form-management/

## Orbeon Forms
أفكار مستفادة:
- Form definition versioning؛
- حماية البيانات القديمة من تغييرات النموذج؛
- دورة Design/Test/Publish/Revise.

مرجع:
- https://doc.orbeon.com/form-runner/features/versioning
- https://www.orbeon.com/form-lifecycle

## Fulcrum
أفكار مستفادة:
- nested sections؛
- drill-down للشاشات المعقدة؛
- repeatable sections كعلاقات Parent/Child.

مرجع:
- https://help.fulcrumapp.com/en/articles/75170-how-do-sections-work
- https://help.fulcrumapp.com/en/articles/75171-what-are-repeatable-sections

## SafetyCulture / iAuditor
أهم درس:
- تعديلات Template المنشورة تطبق على inspections الجديدة، لا تعيد كتابة الماضي.

مرجع:
- https://help.safetyculture.com/en-US/001104/

## SurveyJS Creator
أفكار مستفادة:
- JSON-driven forms؛
- nested panels؛
- Admin builder بصري.

ملاحظة:
- يجب مراجعة الترخيص قبل أي اعتماد مباشر في Production.

مرجع:
- https://github.com/surveyjs/survey-creator

## Form.io
أفكار مستفادة:
- schema-driven builder/renderer؛
- nested components؛
- JSON form definitions.

مرجع:
- https://github.com/formio/formio.js

## Open Forms
أفكار مستفادة:
- مشروع حكومي ديناميكي؛
- فصل Admin/API/SDK؛
- plugin-oriented integrations.

مرجع:
- https://github.com/open-formulieren/open-forms

## QAMIS Inspection Management
مشروع تفتيش مدرسي مباشر على GitHub.

موجود فيه:
- Inspection؛
- Inspection Checklist؛
- School؛
- Teams؛
- approvals/workflow؛
- API.

المستفاد:
- فصل الزيارة عن الفريق والقوائم والمؤسسة.
- لا ننسخ الـapproval workflow في V1 لأن هدفنا الحالي أسرع وأبسط.

مرجع:
- https://github.com/logiic-ltd/qamis-inspection-management

## الخلاصة المعمارية المستفادة

نأخذ الأنماط التالية:
- Recursive structure؛
- dynamic definitions؛
- reusable reference content؛
- Draft/Publish/Version؛
- immutable history؛
- mobile drill-down؛
- central accounts/data.

ولا نحول المشروع إلى Generic No-Code Platform.
