# INSPECTION EXPORT SCHEMA — v2

اسم المخطط:

`inspection-export-v2`

## الهدف

إخراج نسخة منظمة من الزيارة تمثل الحقيقة التشغيلية الفعلية، بما في ذلك نطاق الزيارة وليس البيانات المعبأة فقط.

يمكن:
- أرشفتها؛
- فحصها يدويًا؛
- معالجتها برمجيًا؛
- تمريرها لاحقًا إلى أدوات إعداد التقارير.

## مصدر الحقيقة

التصدير مبني على Inspection Snapshot المثبتة للزيارة، وليس على الصياغة الحالية للـMaster.

تعديل Master لاحقًا لا يعيد تفسير الزيارة القديمة.

## المستوى الأعلى

```json
{
  "schema": "inspection-export-v2",
  "inspection": {}
}
```

## inspection

يتضمن:
- `id`
- `visit_date`
- `status` — قد يكون PENDING / APPROVED / REJECTED / MERGED / WITHDRAWN
- `scope_mode`
- `institution`
- `inspector`
- `master_version`
- `general_observations`
- `general_recommendations`
- `nodes`

## scope_mode

- `LEGACY_FULL`: زيارة تاريخية أُنشئت بالنموذج السابق الكامل.
- `SELECTIVE`: زيارة تعمل بنطاق انتقائي.

## nodes

قائمة Recursive. كل Node يتضمن:
- `snapshot_id`
- `source_stable_id` إن كان مصدره Master
- `title`
- `description`
- `scope`
- `specifications`
- `checklist_items`
- `additional_observations`
- `recommendations`
- `children`

## scope على مستوى Node

```json
{
  "origin": "MANUAL",
  "state": "ACTIVE",
  "locked": false,
  "role": "SELECTED"
}
```

القيم الممكنة لـ `origin`:
- LEGACY
- MANUAL
- GUIDE
- ASSIGNMENT
- LOCAL

القيم الممكنة لـ `state`:
- ACTIVE
- EXCLUDED

القيم الممكنة لـ `role`:
- SELECTED
- CONTEXT

## specifications

كل مواصفة تتضمن Snapshot التعريف التاريخي، القيمة، و:

```json
{
  "scope": {
    "origin": "MANUAL",
    "state": "ACTIVE",
    "locked": false,
    "completion_required": false
  }
}
```

المواصفة EXCLUDED تبقى في التصدير إذا كانت Snapshot موجودة، لأن الإخراج من النطاق لا يمحو الحقيقة التاريخية أو القيمة السابقة.

## checklist_items

كل بند يتضمن:
- Snapshot ID
- Stable ID للمصدر إن وجد
- العنوان التاريخي
- Guidance التاريخي
- الحالة
- المعاينة/الملاحظة
- Scope metadata

بنفس منطق المواصفات، يبقى العنصر EXCLUDED قابلًا للتتبع بدل حذفه.

## Local content وProposal trace

لا يوجد في v2 حقل `local_addition` منفصل.

المعلومة الصحيحة هي:

`scope.origin = "LOCAL"`

وعند وجود Proposal مرتبط بالإضافة المحلية يضاف أثر محدود:
- `proposal_id`
- `status`
- `resolution_data`

## لماذا يتضمن Export العناصر EXCLUDED؟

لأن Soft Exclusion قرار نطاق، وليس حذفًا للبيانات.

وجود العنصر في الملف مع `state = EXCLUDED` يحافظ على:
- البيانات التي سبق إدخالها؛
- أثر تغيير النطاق؛
- إمكانية التفسير اللاحق دون الخلط بين «لم يوجد أصلًا» و«كان موجودًا ثم أُخرج».

## الترتيب

Nodes والمواصفات والبنود تخرج حسب ترتيب Snapshot ثم ID كفاصل ثابت.

لا يوجد `exported_at` حتى يبقى الناتج Deterministic لنفس حالة قاعدة البيانات.

## Encoding

الاستجابة:
- JSON
- UTF-8
- `ensure_ascii=false`

ولا تُصدّر كلمات المرور أو Sessions أو Tokens أو أسرار الاتصال.
