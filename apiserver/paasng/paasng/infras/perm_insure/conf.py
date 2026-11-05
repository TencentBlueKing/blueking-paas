# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.
#
from typing import Set

from paasng.infras.accounts.permissions.constants import SiteAction

# These views either check permissions in their own way or don't need to check permissions
# at all, so they are excluded from the checking process by perm_insure.
INSURE_CHECKING_EXCLUDED_VIEWS: Set[str] = {
    # == DRF views
    # System APIs using basic-auth
    "ExportToDjangoView",
    "ResourceAPIView",
    "PluginCallBackApiViewSet",
    "PluginSelectionView",
    # FIXME: Should update the permission checking logic
    "ApplicationMigrationInfoAPIView",
    # APIs bound with current user/account context, such as creating new applications
    # TODO: This type of views should use a same base class so that we can easily
    # skip the insure checking for them.
    "RegionSpecsViewSet",
    "UserInfoViewSet",
    "AccountFeatureFlagViewSet",
    "ApplicationCreateViewSet",
    "ApplicationListViewSet.list_detailed",
    "ApplicationListViewSet.list_minimal",
    "ApplicationListViewSet.list_search",
    "ApplicationListViewSet.list_idle",
    "ApplicationListViewSet.list_evaluation",
    "ApplicationListViewSet.list_evaluation_issue_count",
    "ApplicationListViewSet.list_statistics",
    "UserVerificationGenerationView",
    "UserVerificationValidationView",
    "Oauth2BackendsViewSet",
    "SMartPackageCreatorViewSet",
    "LatestApplicationsViewSet",
    "SvnAccountViewSet",
    "AccountAllowAppSourceControlView",
    "StatisticsPVAPIView",
    "ApplicationsSearchViewset",
    # [CONFIRMED]: the view have implemented more detailed permission checking in its own way
    "MigrationDetailViewset.state",
    "MigrationDetailViewset.old_state",
    "MigrationDetailViewset.rollback",
    "ProductCombinedViewSet",
    "ProductStateViewSet",
    "ProductCreateViewSet",
    "ApplicationMarkedViewSet",
    "ApplicationGroupByStateStatisticsView",
    "ApplicationGroupByFieldStatisticsView",
    "LegacyAppViewset",
    "MigrationCreateViewset",
    "MigrationConfirmViewset.confirm",
    # Non-sensitive APIs
    "FrontendFeatureViewSet.get_features",
    "FrontendEncryptConfigViewSet.get_encrypt_config",
    "ApplicationMembersViewSet.get_roles",
    "CorpProductViewSet.list",
    "RegionViewSet.retrieve",
    "TenantViewSet.list",
    "TagViewSet",
    "MixDocumentSearch",
    "BkDocsSearchViewset",
    "IWikiSearchViewset",
    "MkSearchViewset",
    "TemplateViewSet",
    "TemplateDetailedViewSet",
    "ChangelogViewSet",
    "DistributorsViewSet",
    "BkPluginTagsViewSet",
    "SchemaViewSet",
    "BkPluginUserManageView",
    "BkAIDevManageView",
    "AppDescTransformAPIView",
    "SMartBuilderViewSet",
    "ProcessComponentViewSet",
    "AssistantView",
    "ReservedAppCodePrefixViewSet",
    #
    # == Django views start
    #
    # A debug page, doesn't need perm checking
    "StreamDebuggerView",
    #
    # == Function-based views
    # below are django system views
    "set_language",
    "get_current_information",
}

# The url prefix of the system APIs, which are called by other systems instead of the users.
SYS_API_URL_PREFIX = "sys/api/"

# The module which provides the sysapi client permissions, used to tell a system API view
# apart from the user-facing ones.
SYSAPI_ROLE_MODULE = "paasng.infras.sysapi_client.roles"

# These views serve the system APIs but don't follow the naming conventions, they are
# excluded from the checking process of `sys_api_layout`.
SYS_API_CHECKING_EXCLUDED_VIEWS: Set[str] = {
    # The deprecated version of the structured log API, it's already registered in APIGW and
    # must keep the same name for compatibility, so the `Sys` prefix is not applicable.
    "V1SysStructuredLogAPIView",
}

# Admin42 drf views' namespaces prefix, used to check if a view is an admin42 view
ADMIN42_MODULE_NAMESPACES = (
    "paasng.plat_admin.admin42.views",
    "paas_wl.apis.admin.views",
)

# Admin42 actions used to check whether a permission is admin42 permission
ADMIN42_ACTIONS = {
    SiteAction.VISIT_ADMIN42,
    SiteAction.MANAGE_PLATFORM,
    SiteAction.MANAGE_APP_TEMPLATES,
    SiteAction.OPERATE_PLATFORM,
}
