from typing import List, Literal

from paas_wl.cnative.specs.constants import MResConditionType, MResPhaseType
from paas_wl.cnative.specs.models import create_app_resource
from paas_wl.cnative.specs.v1alpha1.bk_app import BkAppResource, MetaV1Condition


def create_condition(
    type_: MResConditionType,
    status: Literal["True", "False", "Unknown"] = "Unknown",
    reason: str = '',
    message: str = '',
) -> MetaV1Condition:
    return MetaV1Condition(
        type=type_,
        status=status,
        reason=reason,
        message=message,
    )


def create_res_with_conds(
    conditions: List[MetaV1Condition], phase: MResPhaseType = MResPhaseType.AppPending
) -> BkAppResource:
    mres = create_app_resource(name="foo", image="nginx:latest")
    mres.status.conditions = conditions
    mres.status.phase = phase
    return mres
