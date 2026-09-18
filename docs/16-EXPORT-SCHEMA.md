# INSPECTION EXPORT SCHEMA — v1

اسم المخطط:

`inspection-export-v1`

## الهدف

إخراج نسخة منظمة من الزيارة يمكن:
- أرشفتها؛
- فحصها يدويًا؛
- تمريرها لاحقًا إلى ذكاء اصطناعي خارجي لبناء تقرير؛
- معالجتها برمجيًا دون الاعتماد على HTML.

الموقع في V1 **لا يولد التقرير بالذكاء الاصطناعي داخله**.

## مصدر الحقيقة

التصدير مبني على **Inspection Snapshot** الخاصة بالزيارة، وليس على الصياغة الحالية للـMaster.

لذلك:
- تعديل عنوان مجال لاحقًا لا يغير Export زيارة قديمة؛
- تعديل خيارات مواصفة لاحقًا لا يغير تعريف المواصفة المحفوظ مع الزيارة؛
- تعديل بند لاحقًا لا يغير نص البند التاريخي.

## المستوى الأعلى

```json
{
  "schema": "inspection-export-v1",
  "inspection": {}
}
```

## inspection

يتضمن:
- `id`
- `visit_date`
- `status`
- `institution`
- `inspector`
- `master_version`
- `general_observations`
- `general_recommendations`
- `nodes`

## institution

يتضمن معرف المؤسسة واسمها ونوعها والبلدية كما هي مرتبطة بالزيارة.

## inspector

V1 يخرج:
- `id`
- `username`

ولا يضيف البريد أو كلمة المرور أو Session أو Token.

## master_version

يتضمن:
- معرف إصدار المرجع؛
- رقم الإصدار.

## nodes

قائمة Recursive. كل Node يتضمن:
- `snapshot_id`
- `source_stable_id` إن كان مصدره Master
- `title`
- `description`
- `local_addition`
- `specifications`
- `checklist_items`
- `additional_observations`
- `recommendations`
- `children`

## specifications

كل مواصفة تتضمن:
- Snapshot ID
- Stable ID للمصدر إن وجد
- العنوان
- نوع الحقل
- هل كانت إلزامية
- خياراتها التاريخية
- Help text التاريخي
- القيمة
- Local-addition flag
- Proposal trace إذا كانت إضافة محلية ولها Proposal

## checklist_items

كل بند يتضمن:
- Snapshot ID
- Stable ID للمصدر إن وجد
- العنوان التاريخي
- Guidance التاريخي
- الحالة
- المعاينة/الملاحظة
- Local-addition flag
- Proposal trace إن وجد

## Proposal trace

لا يعيد تصدير Payload الإدارة كاملًا. يعرض أثرًا تشغيليًا محدودًا:
- `proposal_id`
- `status`
- `resolution_data`

## الترتيب

Nodes والمواصفات والبنود تخرج حسب ترتيب Snapshot ثم ID كفاصل ثابت.

لا يوجد `exported_at` في v1 حتى يبقى الناتج Deterministic لنفس حالة قاعدة البيانات.

## Encoding

الاستجابة:
- JSON
- UTF-8
- `ensure_ascii=false`

أي أن العربية تبقى مقروءة مباشرة داخل الملف.
