from django.contrib import admin
from .models import (
    ChecklistItem, Inspection, InspectionItemResult, InspectionNode, Institution,
    MasterVersion, Profile, Proposal, SpecificationDefinition, StructureNode,
)

admin.site.register([
    Profile, Institution, MasterVersion, StructureNode, SpecificationDefinition,
    ChecklistItem, Inspection, InspectionNode, InspectionItemResult, Proposal,
])
