# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
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

# These views either check permissions in their own way or don't need to check permissions
# at all, so they are excluded from the checking process by perm_insure.
INSURE_CHECKING_EXCLUDED_VIEWS: Set[str] = {
    # == DRF views
    # System APIs using basic-auth
    "ExportToDjangoView",
    "ResourceAPIView",
    "PluginCallBackApiViewSet",
    # FIXME: Should update the permission checking logic
    "ApplicationMigrationInfoAPIView",
    # FIXME: bk_plugins permissions
    "DistributorsViewSet",
    "BkPluginTagsViewSet",
    "SchemaViewSet",
    "PluginSelectionView",
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
    "ApplicationMembersViewSet.get_roles",
    "CorpProductViewSet.list",
    "RegionViewSet.retrieve",
    "TagViewSet",
    "MixDocumentSearch",
    "BkDocsSearchViewset",
    "IWikiSearchViewset",
    "MkSearchViewset",
    "StreamViewSet",
    "VoidViewset",
    "ServicePlanViewSet",
    "TemplateViewSet",
    "RegionTemplateViewSet",
    "ChangelogViewSet",
    "ResQuotaPlanOptionsView",
    #
    # == Django views start
    #
    # A debug page, doesn't need perm checking
    "StreamDebuggerView",
    # TODO: The front page of admin, should add perm checking soon
    "FrontPageView",
    # TODO: The dynamic view created by runtime_views.ViewBuilder
    "ListView",
    "UpdateView",
    "CreateView",
    "DeleteView",
    # TODO: The dynamic view created by runtimes.RuntimeAdminViewGenerator
    "APIViewSet",
    #
    # == Function-based views
    # below are django system views
    "set_language",
    "get_current_information",
}
