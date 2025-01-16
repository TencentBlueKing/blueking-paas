"""Custom fields related with multi-tenancy."""

from django.db import models

from .user import DEFAULT_TENANT_ID


def tenant_id_field_factory(db_index: bool = True, unique: bool = False) -> models.CharField:
    """Create a field that is configured to store tenant_id.

    :param db_index: Whether to create an index for the field, defaults to True, turn
        it off when the model already has a compound index on the tenant_id field.
    :param unique: Whether to create a unique index for the field, defaults to False. If unique is True,
        param db_index will be ignored because unique implies the creation of an index.
    """
    if unique:
        return models.CharField(
            verbose_name="租户 ID",
            max_length=32,
            default=DEFAULT_TENANT_ID,
            help_text="本条数据的所属租户",
            unique=True,
        )
    return models.CharField(
        verbose_name="租户 ID",
        max_length=32,
        default=DEFAULT_TENANT_ID,
        help_text="本条数据的所属租户",
        db_index=db_index,
    )
