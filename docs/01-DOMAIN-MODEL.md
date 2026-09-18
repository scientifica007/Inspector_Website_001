# DOMAIN MODEL — v0.1

## 1. الطبقات الثلاث

### A. Master Content
المحتوى المشترك الذي اعتمده Admin:
- المؤسسات المعتمدة؛
- Structure Nodes؛
- Specification Definitions؛
- Checklist Items.

### B. Inspection Data
ما حدث فعليًا في زيارة معينة:
- المؤسسة؛
- المفتش؛
- تاريخ الزيارة؛
- إصدار المرجع المستخدم؛
- قيم المواصفات؛
- نتائج البنود؛
- المعاينات؛
- التوصيات؛
- الإضافات المحلية للزيارة.

### C. Field Proposals
ما اقترحه المفتش من الميدان ليُنظر في تعميمه مستقبلًا:
- مؤسسة؛
- Node؛
- Specification؛
- Checklist Item.

## 2. العنصر الهيكلي Structure Node

العنصر الأساسي للشجرة. لا توجد جداول منفصلة Domain/Subdomain/SubSubdomain.

حقول منطقية مقترحة:
- id
- parent_id nullable
- title
- description
- inspectable boolean
- sort_order
- active
- created_by
- created_at
- updated_at

العلاقة Recursive:
`parent_id -> structure_nodes.id`

وبذلك يمكن تمثيل:
- مجال؛
- تحت مجال؛
- مديرية فرعية؛
- مصلحة؛
- وحدة؛
- أي مستوى إضافي.

## 3. المواصفة Specification Definition

معلومة تصف Node وليست حكمًا تفتيشيًا.

أمثلة:
- اسم ولقب المدير الفرعي؛
- عدد الموظفين؛
- تاريخ التعيين؛
- المصالح الموجودة؛
- وصف تنظيمي.

أنواع V1:
- short_text
- long_text
- number
- date
- boolean
- single_select
- multi_select

حقول مقترحة:
- id
- node_id
- title
- field_type
- required
- options_json nullable
- help_text nullable
- sort_order
- active

## 4. بند التفتيش Checklist Item

شيء يصدر المفتش بشأنه حالة.

حقول مقترحة:
- id
- node_id
- title
- guidance nullable
- sort_order
- active
- created_by
- created_at

الحالات:
- UNCHECKED
- NOT_APPLICABLE
- COMPLIANT
- OBSERVATION
- NON_COMPLIANT

## 5. المؤسسة Institution

كيان مستقل عن الزيارة.

حقول V1 المقترحة:
- id
- name
- type nullable
- commune nullable
- active
- verification_status
- created_by
- created_at

إذا أضافها مفتش أثناء العمل تُستعمل في زيارته فورًا وتولد Proposal للمراجعة.

## 6. المرجع وإصداراته Master Version

الحالة المنطقية:
- DRAFT
- PUBLISHED
- ARCHIVED

كل Publish ينتج Version غير قابلة للتعديل بأثر رجعي.

الزيارة الجديدة تربط:
`inspection.master_version_id`

## 7. الزيارة Inspection

حقول مقترحة:
- id
- institution_id
- inspector_id
- master_version_id
- visit_date
- status: DRAFT | COMPLETED
- general_observations
- general_recommendations
- created_at
- updated_at

## 8. Inspection Node

يمثل Node كما استُعمل داخل الزيارة، ويحتفظ Snapshot مناسبًا لحماية التاريخ.

حقول منطقية:
- id
- inspection_id
- source_node_id nullable
- parent_inspection_node_id nullable
- title_snapshot
- description_snapshot
- sort_order_snapshot
- local_addition boolean
- additional_observations
- recommendations

## 9. Specification Value

- inspection_node_id
- source_specification_id nullable
- title_snapshot
- field_type_snapshot
- value_json
- local_addition boolean

## 10. Inspection Item Result

- inspection_node_id
- source_item_id nullable
- title_snapshot
- status
- observation
- local_addition boolean
- sort_order_snapshot

## 11. Proposal

حقول منطقية:
- id
- type: INSTITUTION | NODE | SPECIFICATION | ITEM
- source_inspection_id
- source_local_id
- proposed_by
- payload_json
- status: PENDING | APPROVED | REJECTED | MERGED
- resolution_note
- resolved_by
- resolved_at

الاعتماد لا يغير الزيارة الأصلية؛ يدخل المحتوى المعتمد في Draft المرجع التالي.

## 12. Invariants

1. الزيارات القديمة لا تتغير عند تعديل Master.
2. أي نص تاريخي مهم يحتفظ Snapshot.
3. لا حذف فعلي لمحتوى مرجعي مستخدم تاريخيًا.
4. عنصر محلي في الزيارة لا يصبح مشتركًا تلقائيًا.
5. Proposal ليست Inspection Data وليست Master Content.
6. Progress يحسب NOT_APPLICABLE كحالة محسومة، بينما Compliance analytics تستبعدها من المقام.
