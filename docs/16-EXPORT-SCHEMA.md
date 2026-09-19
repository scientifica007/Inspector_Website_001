# INSPECTION EXPORT SCHEMA — v4

اسم المخطط:

`inspection-export-v4`

## الهدف

إخراج نسخة منظمة من الزيارة تمثل الحقيقة التشغيلية والتاريخية الفعلية، بما في ذلك:
- نطاق الزيارة؛
- مرجع المصدر التاريخي؛
- التكليفات الرسمية وتاريخ إصدارها/إلغائها.

## مصدر الحقيقة

التصدير مبني على Inspection Snapshots المثبتة للزيارة. تعديل المرجع المصدر أو حذفه لاحقًا لا يعيد تفسير الزيارة.

## المستوى الأعلى

```json
{
  "schema": "inspection-export-v4",
  "inspection": {}
}
```

## inspection

يتضمن:
- `id`
- `visit_date`
- `status`
- `scope_mode`
- `institution`
- `inspector`
- `reference`
- `general_observations`
- `general_recommendations`
- `assignments`
- `nodes`

## reference

`id` هو معرّف المرجع الأصلي إذا كان ما يزال موجودًا، و`name` هو Snapshot لاسمه عند إنشاء الزيارة. اللقطة الداخلية المجمدة لا تُعرض كهوية Business.

## assignments

قائمة سجل التكليفات المرتبطة بالزيارة. كل عنصر يتضمن:
- id
- title / description
- status: DRAFT | ISSUED | REVOKED
- created_by
- issued_by / issued_at
- revoked_by / revoked_at / revocation_reason
- entries

كل Entry يتضمن:
- entry_type
- stable_id
- label
- scope_locked
- completion_required
- sort_order

وجود Assignment في التاريخ لا يعني أن قيوده ما تزال فعالة؛ الحالة الفعالة تظهر أيضًا في Scope metadata لكل Snapshot.

## nodes

كل Node يتضمن Snapshot ID وStable ID للمصدر إن بقي، العنوان والوصف وinspectable وScope metadata والأوصاف والبنود والبيانات الميدانية والأبناء.

Scope metadata تتضمن:
- origin
- state
- locked
- role عند Node
- completion_required عند الوصف والبند

## Local governance history

الإضافات الجديدة داخل الزيارة لا تولد Proposal تلقائيًا. في الزيارات التاريخية قد يبقى Proposal trace القديم حفاظًا على التاريخ.

## الترتيب وEncoding

لا يوجد `exported_at` للمحافظة على Determinism. JSON UTF-8 ولا يحتوي أسرار اتصال أو Sessions أو Tokens.
