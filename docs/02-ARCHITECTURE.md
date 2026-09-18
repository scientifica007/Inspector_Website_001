# ARCHITECTURE — v0.1

## 1. الهدف المعماري

بناء Web App صغيرة الآن، دون إغلاق الطريق أمام التطور لاحقًا.

## 2. المكونات

### Web Client
- واجهة عربية RTL.
- Mobile-first.
- Inspector UI.
- Admin Builder UI.
- Autosave.
- JSON export.

### Application / API Layer
- Authentication.
- Authorization.
- CRUD.
- Versioning.
- Proposal moderation.
- Validation.
- Audit metadata.

### Central Database
يفضل نموذج علائقي يدعم:
- العلاقات Recursive؛
- History؛
- Transactions؛
- صلاحيات؛
- JSON عند الحاجة للقيم الديناميكية.

PostgreSQL هو الاتجاه المرجح، لكن اختيار المزود النهائي يؤجل إلى Technical Spike.

## 3. قرار التقنية المؤجل

لا يُقفل الآن الاختيار بين:
- Backend مُدار مثل Supabase؛
- تطبيق Web مع Backend مخصص؛
- بديل مناسب يثبت في Spike.

معيار الاختيار:
- بساطة النشر؛
- Authentication؛
- PostgreSQL؛
- سياسات صلاحيات جيدة؛
- تكلفة تشغيل منخفضة؛
- سهولة النسخ الاحتياطي؛
- عدم الارتهان غير الضروري؛
- سهولة التطوير بواسطة Agents لاحقًا.

## 4. Versioned Master

لا يوجد "Master حي قابل للتعديل مباشرة".

المسار:
`Published Version → Edit as Draft → Preview → Publish New Version`

الزيارات الجارية لا تنتقل تلقائيًا لإصدار جديد.

## 5. Rendering ديناميكي

الواجهة لا تُبرمج شاشة لكل مجال.

Renderer يقرأ:
- Nodes؛
- Specification definitions؛
- Checklist items؛
- ordering.

ثم يولد UI.

هذا هو أساس قابلية الهندسة بواسطة Admin.

## 6. Security Baseline

- Authentication إلزامي للموقع التشغيلي.
- Authorization Server-side.
- Admin وInspector أدوار منفصلة.
- Validation على الخادم، لا الاعتماد على الواجهة.
- لا أسرار أو Tokens داخل GitHub.
- لا بيانات تشغيلية شخصية حقيقية داخل المستودع.
- سجل من أنشأ/عدل/اعتمد المحتوى المرجعي.
- Export لا يحتوي أكثر مما تحتاجه المهمة.

## 7. تاريخ البيانات

تعديلات Admin المستقبلية لا تعيد تفسير بيانات قديمة.
الـIDs المرجعية وحدها لا تكفي؛ نحتفظ Snapshots للعناوين والتعريفات ذات الصلة.

## 8. التطور اللاحق الممكن

دون تغيير النواة:
- Attachments؛
- PWA/Offline؛
- AI report generation؛
- dashboards؛
- integrations؛
- corrective actions؛
- richer roles.

هذه ليست ضمن V1.
