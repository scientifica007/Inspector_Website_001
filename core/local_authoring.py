from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from .models import (
    InspectionItemResult,
    InspectionNode,
    ResultStatus,
    ScopeOrigin,
    ScopeRole,
    ScopeState,
    SpecificationValue,
)
from .services import (
    exclude_scope_item,
    exclude_scope_node,
    exclude_scope_specification,
)


def node_inspectable(node):
    return bool(node.inspectable_snapshot)


def sync_local_proposal(obj, user, *, inspectable=None):
    """
    Compatibility no-op for A-C3.

    Visit-local authoring is private to the visit and is no longer submitted
    automatically to Admin. Generalization now happens only by explicitly
    submitting a private reference.
    """
    return None, False


def _node_subtree(node):
    found = []
    frontier = [node]
    while frontier:
        current = frontier.pop(0)
        found.append(current)
        frontier.extend(
            list(current.children.all().order_by("sort_order_snapshot", "id"))
        )
    return found


def node_subtree_ids(node):
    return {candidate.id for candidate in _node_subtree(node)}


def _assert_local(obj):
    if obj.scope_origin != ScopeOrigin.LOCAL:
        raise ValidationError(
            "المحتوى المرجعي لا يعدل مباشرة. انسخه كمحتوى محلي ثم عدّل النسخة."
        )


def _assert_active(obj):
    if obj.scope_state != ScopeState.ACTIVE:
        raise ValidationError("لا يمكن تعديل محتوى مستبعد قبل استعادته.")


def _restore_context_path(node):
    chain = []
    current = node
    while current is not None and current.scope_state != ScopeState.ACTIVE:
        if current.scope_role != ScopeRole.CONTEXT:
            raise ValidationError("استعد الفرع الحاوي أولًا.")
        chain.append(current)
        current = current.parent

    for context_node in reversed(chain):
        context_node.scope_state = ScopeState.ACTIVE
        context_node.save(update_fields=["scope_state"])


@transaction.atomic
def update_local_node(node, user, cleaned):
    _assert_local(node)
    _assert_active(node)
    node.title_snapshot = cleaned["title"].strip()
    node.description_snapshot = cleaned["description"].strip()
    node.inspectable_snapshot = bool(cleaned["inspectable"])
    node.save(update_fields=["title_snapshot", "description_snapshot", "inspectable_snapshot"])
    return node


@transaction.atomic
def update_local_specification(value, user, cleaned):
    _assert_local(value)
    _assert_active(value)
    old_type = value.field_type_snapshot
    old_options = list(value.options_snapshot or [])

    value.title_snapshot = cleaned["title"].strip()
    value.field_type_snapshot = cleaned["field_type"]
    value.required_snapshot = cleaned["required"]
    value.options_snapshot = list(cleaned["options"])
    value.help_text_snapshot = cleaned["help_text"].strip()

    update_fields = [
        "title_snapshot",
        "field_type_snapshot",
        "required_snapshot",
        "options_snapshot",
        "help_text_snapshot",
    ]
    if old_type != value.field_type_snapshot or old_options != value.options_snapshot:
        value.value = None
        update_fields.append("value")
    value.save(update_fields=update_fields)
    return value


@transaction.atomic
def update_local_item(item, user, cleaned):
    _assert_local(item)
    _assert_active(item)
    item.title_snapshot = cleaned["title"].strip()
    item.guidance_snapshot = cleaned["guidance"].strip()
    item.save(update_fields=["title_snapshot", "guidance_snapshot"])
    return item


def _copy_specification(source, target, user):
    clone = SpecificationValue.objects.create(
        inspection_node=target,
        source_specification=None,
        title_snapshot=source.title_snapshot,
        field_type_snapshot=source.field_type_snapshot,
        required_snapshot=source.required_snapshot,
        options_snapshot=list(source.options_snapshot or []),
        help_text_snapshot=source.help_text_snapshot,
        value=None,
        sort_order_snapshot=_next_order(
            target.specification_values.all(), "sort_order_snapshot"
        ),
        scope_origin=ScopeOrigin.LOCAL,
        scope_state=ScopeState.ACTIVE,
        scope_locked=False,
        completion_required=False,
    )
    return clone


def _copy_item(source, target, user):
    clone = InspectionItemResult.objects.create(
        inspection_node=target,
        source_item=None,
        title_snapshot=source.title_snapshot,
        guidance_snapshot=source.guidance_snapshot,
        status=ResultStatus.UNCHECKED,
        observation="",
        sort_order_snapshot=_next_order(target.item_results.all(), "sort_order_snapshot"),
        scope_origin=ScopeOrigin.LOCAL,
        scope_state=ScopeState.ACTIVE,
        scope_locked=False,
        completion_required=False,
    )
    return clone


def _copy_node_recursive(source, target_parent, user):
    inspection = source.inspection
    order_query = (
        inspection.inspection_nodes.filter(parent__isnull=True)
        if target_parent is None
        else target_parent.children.all()
    )
    clone = InspectionNode.objects.create(
        inspection=inspection,
        source_node=None,
        parent=target_parent,
        title_snapshot=source.title_snapshot,
        description_snapshot=source.description_snapshot,
        inspectable_snapshot=node_inspectable(source),
        sort_order_snapshot=_next_order(order_query, "sort_order_snapshot"),
        scope_origin=ScopeOrigin.LOCAL,
        scope_state=ScopeState.ACTIVE,
        scope_role=ScopeRole.SELECTED,
        scope_locked=False,
        additional_observations="",
        recommendations="",
    )

    for spec in source.specification_values.filter(
        scope_state=ScopeState.ACTIVE
    ).order_by("sort_order_snapshot", "id"):
        _copy_specification(spec, clone, user)
    for item in source.item_results.filter(
        scope_state=ScopeState.ACTIVE
    ).order_by("sort_order_snapshot", "id"):
        _copy_item(item, clone, user)
    for child in source.children.filter(
        scope_state=ScopeState.ACTIVE
    ).order_by("sort_order_snapshot", "id"):
        _copy_node_recursive(child, clone, user)

    return clone


@transaction.atomic
def copy_node_as_local(source, target_parent, user):
    if source.scope_state != ScopeState.ACTIVE:
        raise ValidationError("لا يمكن نسخ فرع مستبعد.")
    if target_parent is not None:
        if target_parent.inspection_id != source.inspection_id:
            raise ValidationError("وجهة النسخ يجب أن تكون في نفس الزيارة.")
        if target_parent.scope_state != ScopeState.ACTIVE:
            raise ValidationError("لا يمكن النسخ إلى فرع مستبعد.")
    return _copy_node_recursive(source, target_parent, user)


@transaction.atomic
def copy_specification_as_local(source, target, user):
    if source.scope_state != ScopeState.ACTIVE:
        raise ValidationError("لا يمكن نسخ وصف مستبعد.")
    if target.inspection_id != source.inspection_node.inspection_id:
        raise ValidationError("وجهة النسخ يجب أن تكون في نفس الزيارة.")
    if target.scope_state != ScopeState.ACTIVE:
        raise ValidationError("لا يمكن النسخ إلى فرع مستبعد.")
    return _copy_specification(source, target, user)


@transaction.atomic
def copy_item_as_local(source, target, user):
    if source.scope_state != ScopeState.ACTIVE:
        raise ValidationError("لا يمكن نسخ بند مستبعد.")
    if target.inspection_id != source.inspection_node.inspection_id:
        raise ValidationError("وجهة النسخ يجب أن تكون في نفس الزيارة.")
    if target.scope_state != ScopeState.ACTIVE:
        raise ValidationError("لا يمكن النسخ إلى فرع مستبعد.")
    return _copy_item(source, target, user)


@transaction.atomic
def move_local_node(node, target_parent, user):
    _assert_local(node)
    _assert_active(node)
    if target_parent is not None:
        if target_parent.inspection_id != node.inspection_id:
            raise ValidationError("وجهة النقل يجب أن تكون في نفس الزيارة.")
        if target_parent.scope_state != ScopeState.ACTIVE:
            raise ValidationError("لا يمكن النقل إلى فرع مستبعد.")
        if target_parent.id in node_subtree_ids(node):
            raise ValidationError("لا يمكن نقل الفرع داخل نفسه أو داخل أحد فروعه التابعة.")

    if node.parent_id == (target_parent.id if target_parent else None):
        return node, False

    order_query = (
        node.inspection.inspection_nodes.filter(parent__isnull=True)
        if target_parent is None
        else target_parent.children.all()
    )
    node.parent = target_parent
    node.sort_order_snapshot = _next_order(order_query, "sort_order_snapshot")
    node.save(update_fields=["parent", "sort_order_snapshot"])
    return node, True


@transaction.atomic
def move_local_specification(value, target, user):
    _assert_local(value)
    _assert_active(value)
    if target.inspection_id != value.inspection_node.inspection_id:
        raise ValidationError("وجهة النقل يجب أن تكون في نفس الزيارة.")
    if target.scope_state != ScopeState.ACTIVE:
        raise ValidationError("لا يمكن النقل إلى فرع مستبعد.")
    if value.inspection_node_id == target.id:
        return value, False
    value.inspection_node = target
    value.sort_order_snapshot = _next_order(
        target.specification_values.all(), "sort_order_snapshot"
    )
    value.save(update_fields=["inspection_node", "sort_order_snapshot"])
    return value, True


@transaction.atomic
def move_local_item(item, target, user):
    _assert_local(item)
    _assert_active(item)
    if target.inspection_id != item.inspection_node.inspection_id:
        raise ValidationError("وجهة النقل يجب أن تكون في نفس الزيارة.")
    if target.scope_state != ScopeState.ACTIVE:
        raise ValidationError("لا يمكن النقل إلى فرع مستبعد.")
    if item.inspection_node_id == target.id:
        return item, False
    item.inspection_node = target
    item.sort_order_snapshot = _next_order(target.item_results.all(), "sort_order_snapshot")
    item.save(update_fields=["inspection_node", "sort_order_snapshot"])
    return item, True


@transaction.atomic
def remove_local_node(node, user):
    _assert_local(node)
    return exclude_scope_node(node)

@transaction.atomic
def remove_local_specification(value, user):
    _assert_local(value)
    return exclude_scope_specification(value)

@transaction.atomic
def remove_local_item(item, user):
    _assert_local(item)
    return exclude_scope_item(item)

@transaction.atomic
def restore_local_node(node, user):
    _assert_local(node)
    if node.parent_id:
        _restore_context_path(node.parent)
        if node.parent.scope_state != ScopeState.ACTIVE:
            raise ValidationError("استعد الفرع الأب أولًا.")
    subtree = _node_subtree(node)
    for candidate in subtree:
        candidate.scope_state = ScopeState.ACTIVE
        candidate.save(update_fields=["scope_state"])
        for value in candidate.specification_values.filter(scope_origin=ScopeOrigin.LOCAL):
            value.scope_state = ScopeState.ACTIVE
            value.save(update_fields=["scope_state"])
        for item in candidate.item_results.filter(scope_origin=ScopeOrigin.LOCAL):
            item.scope_state = ScopeState.ACTIVE
            item.save(update_fields=["scope_state"])

    return node


@transaction.atomic
def restore_local_specification(value, user):
    _assert_local(value)
    _restore_context_path(value.inspection_node)
    if value.inspection_node.scope_state != ScopeState.ACTIVE:
        raise ValidationError("استعد الفرع الحاوي أولًا.")
    value.scope_state = ScopeState.ACTIVE
    value.save(update_fields=["scope_state"])
    return value


@transaction.atomic
def restore_local_item(item, user):
    _assert_local(item)
    _restore_context_path(item.inspection_node)
    if item.inspection_node.scope_state != ScopeState.ACTIVE:
        raise ValidationError("استعد الفرع الحاوي أولًا.")
    item.scope_state = ScopeState.ACTIVE
    item.save(update_fields=["scope_state"])
    return item
