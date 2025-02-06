"""Custom fields related with multi-tenancy."""

from django.db import models

from .user import DEFAULT_TENANT_ID


def tenant_id_field_factory(db_index: bool = True, unique: bool = False) -> models.CharField:
    """Create a field that is configured to store tenant_id.

    :param db_index: Whether to create an index for the field, defaults to True, turn
        it off when the model already has a compound index on the tenant_id field.
    :param unique: Whether to create a unique index for the field, defaults to False.

    NOTE: https://github.com/TencentBlueKing/blueking-paas/pull/1877#discussion_r1912873811 中有相关的设计讨论
    """
    # If unique is True, db_index should be disabled to avoid creating a redundant index.
    if unique:
        db_index = False
    return models.CharField(
        verbose_name="租户 ID",
        max_length=32,
        default=DEFAULT_TENANT_ID,
        help_text="本条数据的所属租户",
        db_index=db_index,
        unique=unique,
    )
