# INSPECTION EXPORT SCHEMA — v3

اسم المخطط:

`inspection-export-v3`

## الهدف

إخراج نسخة منظمة من الزيارة تمثل الحقيقة التشغيلية الفعلية، بما في ذلك نطاق الزيارة ومرجع المصدر التاريخي دون الاعتماد على بقاء المرجع في المكتبة.

## مصدر الحقيقة

التصدير مبني على Inspection Snapshot المثبتة للزيارة. تعديل المرجع المصدر أو حذفه لاحقًا لا يعيد تفسير الزيارة.

## المستوى الأعلى

```json
{
  "schema": "inspection-export-v3",
  "inspection": {}
}
```

## inspection

يتضمن:
- `id`
- `visit_date`
- `status`: DRAFT | COMPLETED
- `scope_mode`
- `institution`
- `inspector`
- `reference`
- `general_observations`
- `general_recommendations`
- `nodes`

## reference

```json
{
  "id": 12,
  "name": "مرجع زيارة بيداغوجية"
}
```

قد يكون `id` فارغًا إذا حُذف مرجع المصدر أو بدأت الزيارة دون مرجع، بينما يبقى `name` Snapshot للاسم عند إنشاء الزيارة إن كان هناك مصدر.

## scope_mode

- `LEGACY_FULL`: زيارة تاريخية أُنشئت بالنموذج السابق الكامل.
- `SELECTIVE`: زيارة تعمل بنطاق انتقائي.

## nodes

قائمة Recursive. كل Node يتضمن Snapshot ID، Stable ID للمصدر إن بقي موجودًا، العنوان والوصف وScope metadata والأوصاف والبنود والمعاينات والتوصيات والأبناء.

## Local content وProposal trace

`scope.origin = "LOCAL"` يحدد المحتوى المحلي. في البيانات التاريخية التي لها Proposal قد يظهر أثر Proposal المرتبط بها. A-C3.2 يعيد تصميم التعميم ليصبح اختياريًا على مستوى المرجع الخاص بدل الإرسال التلقائي لكل عنصر.

## الحذف

حذف المرجع أو تعريفاته من المكتبة لا يحذف Snapshot الموجودة داخل الزيارة. عند حذف المصدر قد تصبح `source_stable_id` فارغة، لكن العنوان والبيانات التشغيلية التاريخية تبقى في Snapshot.

## الترتيب وEncoding

Nodes والأوصاف والبنود تخرج حسب ترتيب Snapshot ثم ID كفاصل ثابت. لا يوجد `exported_at` للمحافظة على Determinism.

الاستجابة JSON UTF-8 مع `ensure_ascii=false`، ولا تتضمن كلمات مرور أو Sessions أو Tokens أو أسرار اتصال.
