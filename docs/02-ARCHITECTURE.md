# ARCHITECTURE — current contract

## 1. الهدف المعماري

Web App صغيرة قابلة للتوسع، مع فصل واضح بين مكتبة المراجع، مسودة/سجل الزيارة، الحوكمة، والتصدير.

## 2. المكونات

### Web Client
- واجهة عربية RTL.
- Mobile-first.
- Inspector workspace.
- Admin reference builder.
- JSON export.

### Application Layer
- Authentication / Authorization.
- Reference library CRUD.
- Selective visit scope.
- Visit-local authoring.
- ReferenceSubmission governance.
- Institution Proposal governance.
- Validation.
- Audit metadata.

### Central Database
نموذج علائقي يدعم العلاقات Recursive، Transactions، الصلاحيات، Snapshots، وJSON للقيم الديناميكية.
التطبيق الحالي يستخدم Django ORM مع SQLite في Pilot المحلي وقابلية PostgreSQL عند النشر.

## 3. مكتبة المراجع المستقلة

لا يوجد Master حي واحد ولا مسار Published Version → Draft → Publish كعقد حاكم.
المراجع مستقلة: SHARED / PRIVATE / SNAPSHOT داخلية خاصة بالزيارات.
SNAPSHOT ليست عنصرًا في مكتبة المستخدم؛ هي Implementation detail لحماية استقلال الزيارة عن تغييرات المصدر.

## 4. Frozen visit source

عند إنشاء زيارة من Reference:
1. يسجل المصدر في source_reference؛
2. يحفظ reference_name_snapshot؛
3. ينسخ المرجع إلى SNAPSHOT داخلية مستقلة مع Stable IDs نفسها؛
4. يبني المفتش ACTIVE scope انتقائيًا من هذه اللقطة.

لذلك تعديل/حذف المصدر لا يغير الزيارة.

## 5. Rendering ديناميكي

Renderer يقرأ Nodes، Description definitions، Checklist items، ordering، وscope metadata.
ولا توجد شاشة برمجية منفصلة لكل مجال.

## 6. Governance

يوجد مساران منفصلان:
- Institution Proposal للمؤسسات المضافة من الميدان؛
- ReferenceSubmission لتعميم Reference PRIVATE كاملة بناءً على Snapshot ثابتة.

الإضافات LOCAL داخل زيارة لا تُرسل تلقائيًا إلى Admin.

## 7. Security Baseline

- Authentication إلزامي.
- Authorization Server-side.
- Admin وInspector أدوار منفصلة.
- PRIVATE references لا تظهر لغير مالكها.
- SNAPSHOT الداخلية لا تظهر في مكتبة المراجع أو Builder.
- Validation على الخادم.
- لا أسرار/Tokens داخل GitHub.
- Export لا يحتوي إلا ما تحتاجه الزيارة.

## 8. تاريخ البيانات

الحقيقة التاريخية للزيارة تحفظ داخل Inspection snapshots.
Stable IDs تساعد على الربط المنطقي، لكنها لا تستخدم لإعادة تفسير سجل قديم من مرجع حي متغير.
COMPLETED سجل غير قابل للتعديل أو الحذف.

## 9. التطور اللاحق

النواة تسمح لاحقًا بـ Guides، Assignments، Attachments، PWA/Offline، AI report generation، dashboards، integrations، corrective actions، وricher roles.
هذه الإضافات لا يجوز أن تكسر استقلال الزيارة أو تعيد فرض Reference كاملة بلا سبب مهني.
