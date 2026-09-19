# DOMAIN MODEL — v0.2

## 1. الطبقات الرئيسية

### A. Reference Library
مكتبة مراجع التفتيش المستقلة:
- المؤسسات المعتمدة؛
- Structure Nodes؛
- Specification Definitions؛
- Checklist Items.

لا يوجد «Master حالي» يلغي ما قبله. كل مرجع كيان مستقل يمكن أن يكون SHARED أو PRIVATE.

### B. Inspection Data
ما حدث فعليًا في زيارة معينة:
- المؤسسة؛
- المفتش؛
- تاريخ الزيارة؛
- اسم المرجع المصدر كما كان عند إنشاء الزيارة، إن وجد؛
- نطاق الزيارة الفعلي؛
- قيم المواصفات؛
- نتائج البنود؛
- المعاينات؛
- التوصيات؛
- الإضافات المحلية.

### C. Field Proposals
ما اقترحه المفتش من الميدان ليُنظر في تعميمه مستقبلًا:
- مؤسسة؛
- Node؛
- Specification؛
- Checklist Item.

## 2. Structure Node

العنصر الأساسي للشجرة. العلاقة Recursive عبر `parent_id`.

يمكن أن يمثل مجالًا أو تحت مجال أو مصلحة أو وحدة أو أي مستوى إضافي.

## 3. Specification Definition

معلومة تصف Node وليست حكمًا تفتيشيًا.

الأنواع:
- SHORT_TEXT
- LONG_TEXT
- NUMBER
- DATE
- BOOLEAN
- SINGLE_SELECT
- MULTI_SELECT

## 4. Checklist Item

شيء يصدر المفتش بشأنه حالة:
- UNCHECKED
- NOT_APPLICABLE
- COMPLIANT
- OBSERVATION
- NON_COMPLIANT

## 5. Institution

كيان مستقل عن الزيارة. إذا أضافه مفتش أثناء العمل يُستخدم فورًا ويولد Proposal للمراجعة.

## 6. Inspection Reference

يمثل مرجع تفتيش مستقلًا داخل المكتبة.

الحقول الدلالية:
- `name`
- `visibility`: SHARED | PRIVATE
- `owner`: مالك المرجع الخاص، ويكون فارغًا للمرجع الإداري المشترك.

الاسم الداخلي الحالي `MasterVersion` وحقول `number/status/published_at` باقية مؤقتًا لتقليل مخاطر Migration A-C3، لكنها **Legacy metadata غير حاكمة للسلوك**.

لا يؤدي إنشاء مرجع أو تعديله إلى أرشفة أو إلغاء أي مرجع آخر.

## 7. Inspection

الحقول المنطقية الأساسية:
- institution_id
- inspector_id
- master_version_id: مرجع المصدر إن كان ما يزال موجودًا، ويمكن أن يصبح NULL عند حذف المصدر
- reference_name_snapshot: اسم المصدر كما كان عند إنشاء الزيارة
- visit_date
- status: DRAFT | COMPLETED
- scope_mode: LEGACY_FULL | SELECTIVE
- general_observations
- general_recommendations

`SELECTIVE` هو الوضع الافتراضي للزيارات الجديدة. `LEGACY_FULL` يصف الزيارات التاريخية التي أُنشئت قبل الانتقال إلى النطاق الانتقائي.

## 8. Inspection Node

يمثل Node كما استُعمل داخل الزيارة ويحتفظ Snapshot لحماية التاريخ.

إضافة إلى Snapshot، يحمل:
- `scope_origin`: LEGACY | MANUAL | GUIDE | ASSIGNMENT | LOCAL
- `scope_state`: ACTIVE | EXCLUDED
- `scope_role`: SELECTED | CONTEXT
- `scope_locked`: boolean
- additional_observations
- recommendations

`CONTEXT` يعني أن العنصر موجود فقط لحفظ المسار البنيوي لعنصر أعمق، ولا يعني أن بقية محتوياته دخلت نطاق الزيارة.

## 9. Specification Value

يحمل Snapshot للمواصفة وقيمتها، إضافة إلى:
- `scope_origin`
- `scope_state`
- `scope_locked`
- `completion_required`

إخراج المواصفة من النطاق لا يحذف قيمتها.

## 10. Inspection Item Result

يحمل Snapshot للبند وحالته ومعاينته، إضافة إلى:
- `scope_origin`
- `scope_state`
- `scope_locked`
- `completion_required`

إخراج البند من النطاق لا يحذف نتيجته أو معاينته.

## 11. Scope semantics

الأصل هو حرية الاختيار:
- يمكن إضافة فرع كامل؛
- مواصفة منفردة؛
- بند منفرد؛
- أو محتوى محلي غير موجود في المرجع.

عند اختيار عنصر عميق، تُنشأ الآباء اللازمة كسياق فقط.

`scope_locked` يعني أن العنصر لا يجوز إخراجه من النطاق.

`completion_required` مفهوم مستقل: يعني أن الزيارة لا تكتمل قبل حسم العنصر.

التوجيه والإلزام المستقبليان لا يغيران هذه النواة:
- GUIDE يقدّم اقتراحًا قابلًا للتعديل؛
- ASSIGNMENT قد يضيف عناصر مقيدة أو لازمة للإكمال.

## 12. Local content

المحتوى المحلي لا يستخدم Boolean مستقلًا. مصدره يُمثَّل بـ:

`scope_origin = LOCAL`

ويمكن أن يكون:
- Root Node؛
- Child Node؛
- Specification؛
- Checklist Item.

يستخدم فورًا في الزيارة ويولد Proposal. لا يصبح Master Content تلقائيًا.

## 13. Proposal

الـProposal كيان حوكمة منفصل عن Inspection Data وعن Master Content.

الحالات:
- PENDING: قيد المراجعة.
- APPROVED: معتمد.
- REJECTED: مرفوض.
- MERGED: مدمج.
- WITHDRAWN: سحبه المفتش بعد إخراج المحتوى المحلي قبل حسمه إداريًا.

اعتماد Proposal لا يعيد كتابة الزيارة الأصلية؛ يضيف المحتوى المعتمد إلى Draft المرجع التالي.

قد توجد عدة Proposals تاريخية لنفس `source_local_id` عندما يُعدل المحتوى المحلي بعد حسم اقتراح سابق. القرار التاريخي لا يعاد فتحه أو استبداله.

## 14. Invariants

1. لا يوجد مرجع عالمي واحد حاكم؛ المراجع مستقلة.
2. الزيارة قد تختار مرجع مصدر صراحة أو تبدأ دون مرجع.
3. حذف مرجع المصدر لا يحذف الزيارة ولا Snapshot الخاصة بها.
4. Snapshot لا يعاد تفسيره عند تعديل المرجع لاحقًا.
4. اختيار عنصر منفرد لا يسحب محتويات شقيقاته أو بقية الفرع.
5. الآباء السياقية لا تُعامل تلقائيًا كعناصر مفحوصة.
6. الإخراج من النطاق Soft Exclusion ولا يحذف البيانات.
7. الاستعادة تعيد نفس Snapshot وقيمه السابقة.
8. لا يتكرر Snapshot لنفس عنصر Master داخل الزيارة نفسها.
9. Snapshot المرجعي لا يعدل مباشرة؛ التخصيص يتم عبر نسخة LOCAL مستقلة.
10. نسخ المحتوى ينقل التصميم دون قيم أو نتائج ميدانية.
11. نقل المحتوى LOCAL يحافظ على Snapshot نفسها وبياناتها.
12. Soft Remove للمحتوى LOCAL يسحب Proposal المعلق ولا يمحو التاريخ.
9. Progress يحسب ACTIVE checklist items فقط.
10. NOT_APPLICABLE محسومة للـProgress وتستبعد من Compliance denominator.
11. العنصر المحلي لا يصبح مشتركًا دون قرار Admin.
12. Proposal ليست Inspection Data وليست Master Content.
