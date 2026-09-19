import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.models import (
    ChecklistItem,
    FieldType,
    Inspection,
    Institution,
    MasterStatus,
    MasterVersion,
    SpecificationDefinition,
    StructureNode,
)
from core.reference_library import freeze_reference_for_inspection
from core.services import materialize_inspection

User = get_user_model()

class Command(BaseCommand):
    help = "Create a fictitious local pilot dataset in an empty DEBUG database."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="pilot-inspector")
        parser.add_argument(
            "--password",
            default=os.getenv("PILOT_PASSWORD"),
            help="Pilot inspector password. Prefer PILOT_PASSWORD environment variable.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_demo is disabled when DEBUG=False.")

        password = options.get("password")
        if not password:
            raise CommandError(
                "Provide --password or set PILOT_PASSWORD. No password is hard-coded."
            )

        if (
            MasterVersion.objects.exists()
            or Institution.objects.exists()
            or Inspection.objects.exists()
        ):
            raise CommandError(
                "Demo seed requires an empty project database. Existing project data was not changed."
            )

        username = options["username"].strip()
        if not username:
            raise CommandError("Username cannot be empty.")

        user, _ = User.objects.get_or_create(username=username)
        user.set_password(password)
        user.save()

        institution = Institution.objects.create(
            name="مركز التكوين التجريبي",
            institution_type="CFPA — بيانات تجريبية",
            commune="بلدية تجريبية",
        )
        master = MasterVersion.objects.create(
            number=1,
            name="مرجع تجريبي",
            status=MasterStatus.PUBLISHED,
            published_at=timezone.now(),
        )

        admin_node = StructureNode.objects.create(
            master_version=master,
            title="الإدارة والتسيير",
            description="بيانات تجريبية لهندسة مسار التفتيش.",
            sort_order=10,
        )
        studies = StructureNode.objects.create(
            master_version=master,
            parent=admin_node,
            title="المديرية الفرعية للدراسات والتربصات",
            sort_order=10,
        )
        SpecificationDefinition.objects.create(
            node=studies,
            title="اسم ولقب المسؤول",
            field_type=FieldType.SHORT_TEXT,
            required=True,
            sort_order=10,
        )
        SpecificationDefinition.objects.create(
            node=studies,
            title="عدد الموظفين",
            field_type=FieldType.NUMBER,
            sort_order=20,
        )
        SpecificationDefinition.objects.create(
            node=studies,
            title="المصالح الموجودة",
            field_type=FieldType.MULTI_SELECT,
            options=["مصلحة الدراسات", "مصلحة التربصات", "مصلحة أخرى"],
            sort_order=30,
        )
        ChecklistItem.objects.create(
            node=studies,
            title="توفر برنامج عمل قابل للمتابعة",
            guidance="تحقق من وجود برنامج فعلي ومن مؤشرات المتابعة.",
            sort_order=10,
        )
        ChecklistItem.objects.create(
            node=studies,
            title="تحيين السجلات والوثائق",
            sort_order=20,
        )

        workshop = StructureNode.objects.create(
            master_version=master,
            title="الورشات والتجهيزات",
            description="مجال تجريبي للمعاينة التقنية.",
            sort_order=20,
        )
        SpecificationDefinition.objects.create(
            node=workshop,
            title="عدد الورشات المستغلة",
            field_type=FieldType.NUMBER,
            sort_order=10,
        )
        ChecklistItem.objects.create(
            node=workshop,
            title="سلامة شبكة الكهرباء",
            guidance="عاين التوصيلات والحماية والاستعمال الفعلي.",
            sort_order=10,
        )
        ChecklistItem.objects.create(
            node=workshop,
            title="جاهزية التجهيزات للعمل",
            sort_order=20,
        )
        ChecklistItem.objects.create(
            node=workshop,
            title="النظافة ووسائل الوقاية",
            sort_order=30,
        )

        frozen_reference = freeze_reference_for_inspection(master)
        inspection = Inspection.objects.create(
            institution=institution,
            inspector=user,
            master_version=frozen_reference,
            source_reference=master,
            reference_name_snapshot=master.name,
            visit_date=timezone.localdate(),
        )
        materialize_inspection(inspection)

        self.stdout.write(self.style.SUCCESS("Demo pilot dataset created."))
        self.stdout.write(f"Inspector username: {username}")
        self.stdout.write(f"Inspection ID: {inspection.id}")
        self.stdout.write("Password was accepted but is not echoed.")
