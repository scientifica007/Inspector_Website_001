# DECISION LOG — v0.1

## D-001 — Recursive Structure
**قرار:** استخدام Structure Node ذات parent_id بدل Domain/Subdomain ثابتة.

## D-002 — ثلاثة أنواع أساسية داخل Node
**قرار:** فصل:
1. Node؛
2. Specification؛
3. Checklist Item.

## D-003 — الحالات القياسية
**قرار:** الحالات ثابتة في V1:
UNCHECKED / NOT_APPLICABLE / COMPLIANT / OBSERVATION / NON_COMPLIANT.

## D-004 — "غير معني"
**قرار:** حالة مستقلة عن "غير مفحوص".
NOT_APPLICABLE محسومة للـProgress وتستبعد من Compliance denominator.

## D-005 — الإضافة الميدانية لا تتوقف على Admin
**قرار:** المفتش يستخدم الإضافة فورًا داخل زيارته.

## D-006 — Admin هو بوابة التعميم
**قرار:** الإضافة المحلية تولد Proposal؛ Admin يقرر Approve/Edit/Merge/Reject.

## D-007 — Draft / Publish / Version
**قرار:** Master المنشورة لا تعدل مباشرة. Admin يعمل على Draft ثم ينشر Version جديدة.

## D-008 — الزيارة مرتبطة بإصدار
**قرار:** كل Inspection تحفظ master_version_id.

## D-009 — حماية التاريخ
**قرار:** الاحتفاظ Snapshots للعناوين والتعريفات اللازمة داخل الزيارة.

## D-010 — عدم الحذف التاريخي
**قرار:** المحتوى المرجعي المستخدم سابقًا يعطل بدل Hard Delete.

## D-011 — Autosave
**قرار:** الحفظ تلقائي مع مؤشر حالة واضح.

## D-012 — RTL + Mobile-first
**قرار:** الواجهة العربية RTL والهاتف مسار استخدام أساسي لا ثانوي.

## D-013 — التقارير خارج V1
**قرار:** V1 يصدر JSON منظمًا. تحويله إلى تقرير يمكن أن يتم خارجيًا بالذكاء الاصطناعي.

## D-014 — لا Implementation ضخم قبل Spike
**قرار:** بعد Foundation تأتي Technical Spike قصيرة لاختيار Stack، ثم التنفيذ Gate-by-Gate.
