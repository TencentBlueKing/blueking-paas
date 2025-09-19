import logging

from celery import shared_task

from paasng.infras.iam.exceptions import BKIAMGatewayServiceError
from paasng.infras.iam.helpers import delete_role_members, fetch_role_members
from paasng.platform.applications.constants import ApplicationRole
from paasng.platform.applications.models import Application, JustLeaveAppManager
from paasng.platform.applications.signals import application_member_updated
from paasng.platform.applications.tasks import sync_developers_to_sentry
from paasng.utils.error_codes import error_codes

logger = logging.getLogger(__name__)


@shared_task
def remove_temp_admin(app_code: str, username: str):
    """移除临时管理员权限"""

    try:
        application = Application.objects.get(code=app_code)
    except Application.DoesNotExist:
        logger.warning(f"Application with code {app_code} does not exist, skip removing temp admin")
        return

    # 检查用户是否是唯一管理员
    administrators = fetch_role_members(app_code, ApplicationRole.ADMINISTRATOR)
    if len(administrators) <= 1 and username in administrators:
        raise error_codes.MEMBERSHIP_DELETE_FAILED

    try:
        delete_role_members(app_code, ApplicationRole.ADMINISTRATOR, username)
    except BKIAMGatewayServiceError as e:
        raise error_codes.DELETE_APP_MEMBERS_ERROR.f(e.message)

    # 将该应用 Code 标记为刚退出，避免出现退出用户组，权限中心权限未同步的情况
    JustLeaveAppManager(username).add(app_code)
    sync_developers_to_sentry.delay(application.id)
    application_member_updated.send(sender=application, application=application)
    logger.info(f"Successfully removed temporary admin permission for user {username} from app {app_code}")
