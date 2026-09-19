from django.urls import path
from . import builder_views, export_views, governance_views, local_views, views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("health/", views.health, name="health"),
    path("references/", views.reference_list, name="reference_list"),
    path("institutions/", views.institution_list, name="institution_list"),
    path("institutions/new/", views.institution_create, name="institution_create"),
    path("inspections/", views.inspection_list, name="inspection_list"),
    path("inspections/new/", views.inspection_create, name="inspection_create"),
    path("inspections/<int:pk>/", views.inspection_detail, name="inspection_detail"),
    path("inspections/<int:pk>/prepare/", views.inspection_prepare, name="inspection_prepare"),
    path("inspections/<int:pk>/execute/", views.inspection_execute, name="inspection_execute"),
    path("inspections/<int:pk>/scope/", views.inspection_scope, name="inspection_scope"),
    path("inspections/<int:pk>/export.json", export_views.inspection_export, name="inspection_export"),
    path(
        "inspections/<int:inspection_pk>/nodes/<int:node_pk>/",
        views.inspection_node,
        name="inspection_node",
    ),
    path(
        "inspections/<int:inspection_pk>/nodes/<int:node_pk>/prepare/",
        views.inspection_node_prepare,
        name="inspection_node_prepare",
    ),
    path(
        "inspections/<int:pk>/general/",
        views.inspection_general,
        name="inspection_general",
    ),
    path(
        "inspections/<int:pk>/complete/",
        views.inspection_complete,
        name="inspection_complete",
    ),
    path(
        "inspections/<int:inspection_pk>/add-root-node/",
        local_views.local_root_node_add,
        name="local_root_node_add",
    ),
    path(
        "inspections/<int:inspection_pk>/nodes/<int:node_pk>/add-node/",
        local_views.local_node_add,
        name="local_node_add",
    ),
    path(
        "inspections/<int:inspection_pk>/nodes/<int:node_pk>/add-specification/",
        local_views.local_specification_add,
        name="local_spec_add",
    ),
    path(
        "inspections/<int:inspection_pk>/nodes/<int:node_pk>/add-item/",
        local_views.local_item_add,
        name="local_item_add",
    ),

    path(
        "inspections/<int:inspection_pk>/local-removed/",
        local_views.local_removed_content,
        name="local_removed_content",
    ),
    path(
        "inspections/<int:inspection_pk>/nodes/<int:node_pk>/edit-local/",
        local_views.local_node_edit,
        name="local_node_edit",
    ),
    path(
        "inspections/<int:inspection_pk>/nodes/<int:node_pk>/duplicate-local/",
        local_views.local_node_duplicate,
        name="local_node_duplicate",
    ),
    path(
        "inspections/<int:inspection_pk>/nodes/<int:node_pk>/copy-local/",
        local_views.local_node_copy,
        name="local_node_copy",
    ),
    path(
        "inspections/<int:inspection_pk>/nodes/<int:node_pk>/move-local/",
        local_views.local_node_move,
        name="local_node_move",
    ),
    path(
        "inspections/<int:inspection_pk>/nodes/<int:node_pk>/remove-local/",
        local_views.local_node_remove,
        name="local_node_remove",
    ),
    path(
        "inspections/<int:inspection_pk>/nodes/<int:node_pk>/restore-local/",
        local_views.local_node_restore,
        name="local_node_restore",
    ),
    path(
        "inspections/<int:inspection_pk>/descriptions/<int:spec_pk>/edit-local/",
        local_views.local_specification_edit,
        name="local_spec_edit",
    ),
    path(
        "inspections/<int:inspection_pk>/descriptions/<int:spec_pk>/duplicate-local/",
        local_views.local_specification_duplicate,
        name="local_spec_duplicate",
    ),
    path(
        "inspections/<int:inspection_pk>/descriptions/<int:spec_pk>/copy-local/",
        local_views.local_specification_copy,
        name="local_spec_copy",
    ),
    path(
        "inspections/<int:inspection_pk>/descriptions/<int:spec_pk>/move-local/",
        local_views.local_specification_move,
        name="local_spec_move",
    ),
    path(
        "inspections/<int:inspection_pk>/descriptions/<int:spec_pk>/remove-local/",
        local_views.local_specification_remove,
        name="local_spec_remove",
    ),
    path(
        "inspections/<int:inspection_pk>/descriptions/<int:spec_pk>/restore-local/",
        local_views.local_specification_restore,
        name="local_spec_restore",
    ),
    path(
        "inspections/<int:inspection_pk>/items/<int:item_pk>/edit-local/",
        local_views.local_item_edit,
        name="local_item_edit",
    ),
    path(
        "inspections/<int:inspection_pk>/items/<int:item_pk>/duplicate-local/",
        local_views.local_item_duplicate,
        name="local_item_duplicate",
    ),
    path(
        "inspections/<int:inspection_pk>/items/<int:item_pk>/copy-local/",
        local_views.local_item_copy,
        name="local_item_copy",
    ),
    path(
        "inspections/<int:inspection_pk>/items/<int:item_pk>/move-local/",
        local_views.local_item_move,
        name="local_item_move",
    ),
    path(
        "inspections/<int:inspection_pk>/items/<int:item_pk>/remove-local/",
        local_views.local_item_remove,
        name="local_item_remove",
    ),
    path(
        "inspections/<int:inspection_pk>/items/<int:item_pk>/restore-local/",
        local_views.local_item_restore,
        name="local_item_restore",
    ),

    path("builder/", builder_views.builder_home, name="builder_home"),
    path("builder/references/new/", builder_views.reference_create, name="builder_reference_create"),
    path("builder/references/<int:reference_pk>/", builder_views.reference_detail, name="builder_reference"),
    path("builder/references/<int:reference_pk>/edit/", builder_views.reference_edit, name="builder_reference_edit"),
    path("builder/references/<int:reference_pk>/delete/", builder_views.reference_delete, name="builder_reference_delete"),
    path("builder/references/<int:reference_pk>/preview/", builder_views.reference_preview, name="builder_reference_preview"),
    path("builder/references/<int:reference_pk>/nodes/new/", builder_views.node_create, name="builder_node_create"),
    path("builder/nodes/<int:pk>/", builder_views.node_detail, name="builder_node"),
    path("builder/nodes/<int:pk>/edit/", builder_views.node_edit, name="builder_node_edit"),
    path("builder/nodes/<int:pk>/toggle/", builder_views.node_toggle, name="builder_node_toggle"),
    path("builder/nodes/<int:pk>/delete/", builder_views.node_delete, name="builder_node_delete"),
    path("builder/nodes/<int:node_pk>/descriptions/new/", builder_views.specification_create, name="builder_spec_create"),
    path("builder/descriptions/<int:pk>/edit/", builder_views.specification_edit, name="builder_spec_edit"),
    path("builder/descriptions/<int:pk>/toggle/", builder_views.specification_toggle, name="builder_spec_toggle"),
    path("builder/descriptions/<int:pk>/delete/", builder_views.specification_delete, name="builder_spec_delete"),
    path("builder/nodes/<int:node_pk>/items/new/", builder_views.item_create, name="builder_item_create"),
    path("builder/items/<int:pk>/edit/", builder_views.item_edit, name="builder_item_edit"),
    path("builder/items/<int:pk>/toggle/", builder_views.item_toggle, name="builder_item_toggle"),
    path("builder/items/<int:pk>/delete/", builder_views.item_delete, name="builder_item_delete"),

    path("proposals/", governance_views.proposal_list, name="proposal_list"),
    path("proposals/<int:pk>/", governance_views.proposal_detail, name="proposal_detail"),
]
