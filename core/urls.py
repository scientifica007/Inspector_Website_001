from django.urls import path
from . import builder_views, views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("health/", views.health, name="health"),
    path("institutions/", views.institution_list, name="institution_list"),
    path("institutions/new/", views.institution_create, name="institution_create"),
    path("inspections/new/", views.inspection_create, name="inspection_create"),

    path("builder/", builder_views.builder_home, name="builder_home"),
    path("builder/draft/new/", builder_views.draft_create, name="builder_draft_create"),
    path("builder/preview/", builder_views.draft_preview, name="builder_preview"),
    path("builder/nodes/new/", builder_views.node_create, name="builder_node_create"),
    path("builder/nodes/<int:pk>/", builder_views.node_detail, name="builder_node"),
    path("builder/nodes/<int:pk>/edit/", builder_views.node_edit, name="builder_node_edit"),
    path("builder/nodes/<int:pk>/toggle/", builder_views.node_toggle, name="builder_node_toggle"),
    path("builder/nodes/<int:node_pk>/specifications/new/", builder_views.specification_create, name="builder_spec_create"),
    path("builder/specifications/<int:pk>/edit/", builder_views.specification_edit, name="builder_spec_edit"),
    path("builder/specifications/<int:pk>/toggle/", builder_views.specification_toggle, name="builder_spec_toggle"),
    path("builder/nodes/<int:node_pk>/items/new/", builder_views.item_create, name="builder_item_create"),
    path("builder/items/<int:pk>/edit/", builder_views.item_edit, name="builder_item_edit"),
    path("builder/items/<int:pk>/toggle/", builder_views.item_toggle, name="builder_item_toggle"),
]
