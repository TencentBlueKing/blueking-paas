# -*- coding: utf-8 -*-
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

import datetime
import logging
from pathlib import Path
from urllib.parse import urlparse

from blue_krill.storages.blobstore.exceptions import UploadFailedError
from django.conf import settings
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from svn.common import SvnException

from paasng.core.tenant.user import get_tenant
from paasng.infras.accounts.constants import FunctionType
from paasng.infras.accounts.models import Oauth2TokenHolder, make_verifier
from paasng.infras.accounts.oauth.utils import get_backend
from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.infras.notifier.client import BkNotificationService
from paasng.infras.notifier.exceptions import BaseNotifierError
from paasng.misc.audit.constants import OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_app_audit_record
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.models import Module
from paasng.platform.modules.specs import ModuleSpecs
from paasng.platform.modules.utils import get_module_init_repo_context
from paasng.platform.sourcectl import serializers as slzs
from paasng.platform.sourcectl.connector import get_repo_connector
from paasng.platform.sourcectl.docker.models import init_image_repo
from paasng.platform.sourcectl.exceptions import (
    AccessTokenForbidden,
    OauthAuthorizationRequired,
    PackageAlreadyExists,
    UserNotBindedToSourceProviderError,
)
from paasng.platform.sourcectl.models import SvnAccount, VersionInfo
from paasng.platform.sourcectl.package.uploader import upload_package_via_url
from paasng.platform.sourcectl.perm import UserSourceProviders, render_providers
from paasng.platform.sourcectl.repo_controller import get_repo_controller, list_git_repositories
from paasng.platform.sourcectl.signals import empty_svn_accounts_fetched, repo_updated, svn_account_updated
from paasng.platform.sourcectl.source_types import get_sourcectl_type, get_sourcectl_types
from paasng.platform.sourcectl.svn.admin import promote_repo_privilege_temporary
from paasng.platform.sourcectl.svn.client import RepoProvider
from paasng.platform.sourcectl.type_specs import BkSvnSourceTypeSpec
from paasng.platform.sourcectl.version_services import get_version_service
from paasng.platform.templates.constants import TemplateType
from paasng.platform.templates.templater import upload_init_code_to_storage
from paasng.utils.error_codes import error_codes

#############
# API Views #
#############
logger = logging.getLogger(__name__)


class SvnAccountViewSet(viewsets.ModelViewSet):
    """
    SVN账户 相关
    list: 账户列表
    - [测试地址](/api/users/source/svn/accounts)
    - 创建SVN账户不需要传validation_code字段(不需要短信验证码)
    create: 注册账户
    - 注册完成后密码直接通过短信或微信的形式发送到用户的手机上，后台不记录密码
    - [测试地址](/api/users/source/svn/accounts)
    update: 重置密码
    - 重置后密码直接通过短信或微信的形式发送到用户的手机上，后台不记录密码
    - [测试地址](/api/sourcectl/bksvn/accounts/(?P<id>\\d+)/reset/)
    """

    required_session_code_verifier_methods = ["update"]
    queryset = SvnAccount.objects.all()
    serializer_class = slzs.SvnAccountSLZ
    pagination_class = None
    lookup_field = "id"

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user.pk)

    def list(self, request, *args, **kwargs):
        accounts = list(self.get_queryset())
        if not accounts:
            results = empty_svn_accounts_fetched.send(sender=self, username=request.user.username)
            for __, response in results:
                if isinstance(response, SvnAccount):
                    accounts = [response]
        list_serializer = slzs.SvnAccountSLZ(accounts, many=True, context=self.get_serializer_context())
        return Response(list_serializer.data)

    def process_password(self, account, password):
        """对返回的密码信息进行加工处理"""
        user = self.request.user
        message = _("您的蓝鲸开发账户, SVN账号是{account}, 密码是：{password}, 请妥善保管。").format(
            account=account, password=password
        )

        user_tenant_id = get_tenant(user).id
        bk_notify = BkNotificationService(user_tenant_id)
        try:
            bk_notify.send_wecom([user.username], message, _("蓝鲸平台"))
        except BaseNotifierError:
            raise error_codes.ERROR_SENDING_NOTIFICATION

        return {
            "user": user.username,
            "account": account,
            "password": password,
        }

    def notify_svn_account_changed(self, username, account, password, created):
        svn_account_updated.send(sender=self, username=username, account=account, password=password, created=created)

    @swagger_auto_schema(response_serializer=slzs.SVNAccountResponseSLZ)
    def update(self, request, *args, **kwargs):
        """输入验证码后重置 SVN 密码。"""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = slzs.SvnAccountSLZ(
            instance, data=request.data, partial=partial, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if settings.ENABLE_VERIFICATION_CODE:
            verifier = make_verifier(request.session, FunctionType.SVN.value)
            code = data["verification_code"]
            if not verifier.validate_and_clean(code):
                raise ValidationError({"verification_code": [_("验证码错误")]})

        account_info = SvnAccount.objects.reset_account(instance=instance, user=request.user)

        self.notify_svn_account_changed(
            username=request.user.username,
            account=account_info["account"],
            password=account_info["password"],
            created=False,
        )

        result = self.process_password(account=account_info["account"], password=account_info["password"])
        result["id"] = account_info["id"]
        response_serializer = slzs.SVNAccountResponseSLZ(result)
        return Response(response_serializer.data)


class GitRepoViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    def handle_exception(self, exc):
        # Return a well-formatted response for OauthAuthorizationRequired exception
        if isinstance(exc, OauthAuthorizationRequired):
            return Response(
                {
                    "message": _("用户未关联 oauth 授权"),
                    "address": exc.authorization_url,
                    "auth_docs": exc.auth_docs,
                    "result": True,
                },
                403,
            )
        else:
            return super().handle_exception(exc)

    def get_repo_list(self, request, source_control_type):
        """通过用户绑定的 access_token 查询对应仓库列表
        :param source_control_type: 源码类型
        """
        try:
            repos = list_git_repositories(source_control_type=source_control_type, operator=request.user.pk)
        except Oauth2TokenHolder.DoesNotExist:
            logger.debug(
                f"User is not bound to token_holder of type: {source_control_type}, detail: TokenHolder Not Found"
            )
            if source_control_type in UserSourceProviders(user=request.user).list_available():
                backend = get_backend(source_control_type)
                raise OauthAuthorizationRequired(
                    authorization_url=backend.get_authorization_url(), auth_docs=backend.get_auth_docs()
                )
            raise PermissionDenied
        except AccessTokenForbidden as e:
            raise error_codes.CANNOT_GET_REPO.f(_("当前 AccessToken 无法获取到仓库列表，请检查后重试")) from e
        except Exception as e:
            logger.exception(
                "Unknown error occurred when getting repo list, user_id: %s, sourcectl_type: %s",
                request.user.pk,
                source_control_type,
            )
            raise error_codes.CANNOT_GET_REPO.f(_("访问源码仓库失败，请联系项目管理员")) from e

        return Response({"results": slzs.RepoSLZ(repos, many=True).data})


class AccountAllowAppSourceControlView(APIView):
    """返回 用户支持的 APP 仓储列表"""

    def get(self, request):
        provider_types = set(UserSourceProviders(request.user).list_available())
        results = render_providers(sorted(provider_types))
        return Response(data={"results": results})


class ModuleSourceProvidersViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """获取某个应用模块可用的源码仓库"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    def list(self, request, code, module_name):
        module = self.get_module_via_path()
        provider_types = set(UserSourceProviders(request.user).list_module_available(module))
        results = render_providers(sorted(provider_types))
        return Response(data={"results": results})


@method_decorator(name="list", decorator=swagger_auto_schema(tags=["源码包管理"]))
class ModuleSourcePackageViewSet(viewsets.ModelViewSet, ApplicationCodeInPathMixin):
    """管理某个应用模块的源码包"""

    serializer_class = slzs.SourcePackageSLZ
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["version", "package_name", "package_size"]
    ordering = ("-created",)
    ordering_fields = ("version", "package_name", "package_size", "updated")
    parser_classes = [MultiPartParser, JSONParser]

    def get_module(self):
        module = self.get_module_via_path()
        if not ModuleSpecs(module).deploy_via_package:
            raise error_codes.UNSUPPORTED_SOURCE_ORIGIN
        return module

    def get_queryset(self):
        return self.get_module().packages.all()

    def handle_exception(self, exc):
        if isinstance(exc, PackageAlreadyExists):
            raise error_codes.PACKAGE_ALREADY_EXISTS
        if isinstance(exc, UploadFailedError):
            raise error_codes.OBJECT_STORE_EXCEPTION.f(_("请联系管理员")) from exc
        return super().handle_exception(exc)

    @swagger_auto_schema(
        request_body=slzs.SourcePackageUploadViaUrlSLZ,
        responses={200: slzs.SourcePackageSLZ()},
        tags=["源码包管理"],
        operation_description="目前仅提供给 lesscode 项目使用",
    )
    def upload_via_url(self, request, code, module_name):
        """根据 URL 方式上传源码包, 目前不校验 app_desc.yaml"""
        module = self.get_module()
        slz = slzs.SourcePackageUploadViaUrlSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data
        allow_overwrite = data["allow_overwrite"]
        version = data["version"]
        package_url = data["package_url"]

        # 提取文件名
        filename = Path(urlparse(package_url).path).name.split(".")[0]
        # 保证文件名中会记录版本信息.
        filename = f"{filename}:{version}" if version not in filename else filename
        source_package = upload_package_via_url(
            module, package_url, version, filename, request.user, allow_overwrite=allow_overwrite, need_patch=False
        )
        return Response(data=slzs.SourcePackageSLZ(source_package).data)


class ModuleInitTemplateViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """重新生成应用模块初始化代码，并提供下载地址"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    def download(self, request, code, module_name):
        application = self.get_application()
        module = application.get_module(module_name)
        return self._create_downloadable_address(module)

    def download_default(self, request, code):
        module = self.get_application().get_default_module()
        return self._create_downloadable_address(module)

    def _create_downloadable_address(self, module: Module) -> Response:
        """生成新的可下载初始化模版源码包地址"""
        context = get_module_init_repo_context(module, TemplateType.NORMAL)
        try:
            result = upload_init_code_to_storage(module, context)
        except Exception as e:
            raise error_codes.CANNOT_INIT_APP_TEMPLATE.f(str(e))
        if not result.is_success():
            raise error_codes.CANNOT_INIT_APP_TEMPLATE.f(result.error)
        return Response(result.extra_info)


class RepoBackendControlViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """源码仓库控制"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @swagger_auto_schema(request_body=slzs.RepoBackendModifySLZ(), tags=["sourcectl"])
    def modify(self, request, code, module_name):
        application = self.get_application()
        module = application.get_module(module_name)

        if not application.engine_enabled:
            raise error_codes.CANNOT_MODIFY_REPO_BACKEND.f(_("无引擎应用不支持切换源码类型"))

        if module.get_source_origin() == SourceOrigin.IMAGE_REGISTRY:
            return self._modify_image(request, code, module_name)

        slz = slzs.RepoBackendModifySLZ(data=self.request.data, context={"is_image_repo": False})
        slz.is_valid(raise_exception=True)
        data = slz.data
        repo_type = data["source_control_type"]
        repo_url = data["source_repo_url"]

        data_before = None
        if source_obj := module.get_source_obj():
            data_before = DataDetail(
                data={
                    "repo_type": source_obj.get_source_type(),
                    "repo_url": source_obj.get_repo_url(),
                    "source_dir": source_obj.get_source_dir(),
                },
            )

        if isinstance(get_sourcectl_type(repo_type), BkSvnSourceTypeSpec):
            # 支持用户进行 Svn -> Git 仓库修改, 或Git -> Git 仓库修改, 不支持 Git -> Svn 修改
            raise error_codes.CANNOT_MODIFY_REPO_BACKEND.format(_("不支持切换到蓝鲸 SVN 仓库"))

        try:
            get_repo_connector(repo_type, module).bind(
                repo_url, repo_auth_info=data["source_repo_auth_info"], source_dir=data["source_dir"]
            )
        except Exception:
            logger.exception("Fail to bind repo")
            raise error_codes.CANNOT_BIND_REPO.f(_("请稍候再试"))

        repo_updated.send(sender=self, module_id=module.id, operator=request.user.username)

        add_app_audit_record(
            app_code=application.code,
            tenant_id=application.tenant_id,
            user=request.user.pk,
            action_id=AppAction.BASIC_DEVELOP,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.APP_DOMAIN,
            module_name=module_name,
            data_before=data_before,
            data_after=DataDetail(
                data={"repo_type": repo_type, "repo_url": repo_url, "source_dir": data["source_dir"]},
            ),
        )
        return Response(
            data={"message": _("仓库成功更改为 {}").format(repo_url), "repo_type": repo_type, "repo_url": repo_url}
        )

    def _modify_image(self, request, code, module_name):
        module = self.get_module_via_path()
        slz = slzs.RepoBackendModifySLZ(data=request.data, context={"is_image_repo": True})
        slz.is_valid(raise_exception=True)
        data = slz.data
        repo_url = data["source_repo_url"]

        init_image_repo(
            module,
            repo_url=repo_url,
            source_dir=data["source_dir"],
            repo_auth_info=data["source_repo_auth_info"],
        )
        return Response(data={"message": f"仓库成功更改为 {repo_url}", "repo_type": "", "repo_url": repo_url})


class RepoDataViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    def get_repo_branches(self, request, code, module_name):
        """获取蓝鲸应用的代码分支信息"""
        application = self.get_application()
        module = application.get_module(module_name)
        try:
            version_service = get_version_service(module, operator=request.user.pk)
            alternative_versions = slzs.AlternativeVersionSLZ(
                version_service.list_alternative_versions(),
                many=True,
                context={"is_smart_app": application.is_smart_app},
            ).data
        except UserNotBindedToSourceProviderError:
            raise error_codes.NEED_TO_BIND_OAUTH_INFO
        except AccessTokenForbidden:
            raise error_codes.CANNOT_GET_REPO.f(_("AccessToken无权限访问该仓库, 请检查授权与其对应 Scope"))
        except SvnException:
            raise error_codes.CANNOT_GET_REPO.f(_("无法获取 SVN 分支信息, 请检查仓库地址和鉴权信息"))
        except Exception:
            logger.exception("unable to fetch repo info, may be the credential error or a network exception.")
            raise error_codes.CANNOT_GET_REPO.f(_("%s的仓库信息查询异常") % code)
        else:
            return Response({"results": alternative_versions})

    def get_diff_commit_logs(self, request, code, module_name, from_revision, to_revision):
        """获取蓝鲸应用2个代码版本之间的提交记录(大于from_revision, 小于等于to_revision之间的提交纪录)
        ----
        {
            'results': [
                {
                    date: "17/08/15 08:11:31",
                    message: "Init with template",
                    author: "svn_t",
                    changelist: [
                        [
                            "A",
                            "/apps/ngdemo/trunk/__apps/trunk/Procfile"
                        ],
                        [
                            "A",
                            "/apps/ngdemo/trunk/__apps/trunk/bin"
                        ],
                    ],
                    revision: 201328
                }
            ]
        }
        """
        application = self.get_application()
        repo_controller = get_repo_controller(application.get_module(module_name), operator=request.user.pk)

        def format_smart_revision(revision):
            """Transform smart revisions such as "trunk:trunk"、"tags:1234" to the recent
            revision numbers.
            """
            if revision.isdigit():
                # 转换成 int 类型，不然后面的过滤 from_revision 的逻辑会失效
                return int(revision)
            try:
                return repo_controller.extract_smart_revision(revision)
            except ValueError:
                raise ValidationError('given revision "%s" is not a valid revision number or branch name.' % revision)

        from_revision = format_smart_revision(from_revision)
        # to_revision must be look like `version_type:version_name`
        version_type, version_name = to_revision.split(":")
        to_version = VersionInfo(format_smart_revision(to_revision), version_name, version_type)
        # 通过 version 解析出 svn 需要的相对路径 `rel_filepath`
        target_branch_or_path, to_revision = repo_controller.extract_version_info(to_version)

        commit_logs = repo_controller.get_diff_commit_logs(
            from_revision, to_revision, rel_filepath=target_branch_or_path
        )
        # 不包含 from_revision 中提交的内容
        commit_logs = [_log for _log in commit_logs if _log.revision != from_revision]
        # 对日期逆序排序
        commit_logs = sorted(commit_logs, key=lambda x: x.date, reverse=True)
        return Response({"results": slzs.CommitLogSLZ(commit_logs, many=True).data})

    def get_compare_url(self, request, code, module_name, from_revision, to_revision):
        """获取外部 Git 系统提供的 compare url"""
        application = self.get_application()
        repo_controller = get_repo_controller(application.get_module(module_name), operator=request.user.pk)
        # 接入其他系统时，需要在对应的 repo_controller 实现这个接口
        try:
            compare_url = repo_controller.build_compare_url(from_revision, to_revision)
        except AccessTokenForbidden:
            raise error_codes.CANNOT_GET_REPO.f(_("AccessToken无权限访问该仓库, 请检查授权与其对应 Scope"))
        except Exception as e:
            logger.exception("Unknown error occurred when getting compare url, user_id: %s", request.user.pk)
            raise error_codes.CANNOT_GET_REPO.f(_(f"仓库信息查询异常: {e}"))
        return Response({"result": compare_url})


class SVNRepoTagsView(APIView, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    def post(self, request, code, module_name):
        """
        对代码镜像打tag包
        """
        application = self.get_application()
        module = application.get_module(module_name)

        svn_type_spec = get_sourcectl_types().find_by_type(BkSvnSourceTypeSpec)
        if module.source_type != svn_type_spec.name:
            message = _("{source_type} 类型源码暂不支持打包操作").format(source_type=module.source_type)
            return Response({"message": message}, status=status.HTTP_501_NOT_IMPLEMENTED)

        with promote_repo_privilege_temporary(application):
            time_str = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            data = {"tag_name": time_str, "comment": time_str}
            provider = RepoProvider(**svn_type_spec.config_as_arguments())

            try:
                result = provider.make_tag_from_trunk(
                    module.get_source_obj().get_repo_url(), tag_name=data["tag_name"], comment=data["comment"]
                )
            except Exception as e:
                logger.exception("App: %s, module: %s create svn tag error", application.code, module.name)
                raise error_codes.CANNOT_CREATE_SVN_TAG.f(str(e))

        return Response(
            {
                "request_data": data,
                "output": result,
            },
            status=status.HTTP_201_CREATED,
        )


class RevisionInspectViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """This ViewSet provides a service for querying details of deployable versions"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    def retrieve(self, request, code, module_name, smart_revision):
        module = self.get_module_via_path()
        try:
            version_service = get_version_service(module, operator=request.user.pk)
        except NotImplementedError:
            raise error_codes.UNSUPPORTED_SOURCE_TYPE

        version_type, version_name = smart_revision.split(":")
        revision = version_service.extract_smart_revision(smart_revision)
        version_info = VersionInfo(version_name=version_name, version_type=version_type, revision=revision)

        try:
            data = slzs.AlternativeVersionSLZ(version_service.inspect_version(version_info=version_info)).data
        except UserNotBindedToSourceProviderError:
            raise error_codes.NEED_TO_BIND_OAUTH_INFO
        except AccessTokenForbidden:
            raise error_codes.CANNOT_GET_REPO.f(_("AccessToken无权限访问该仓库, 请检查授权与其对应 Scope"))
        except Exception:
            logger.exception(
                "Unknown error occurred when inspecting version, user_id: %s, version: %s",
                request.user.pk,
                smart_revision,
            )
            raise error_codes.CANNOT_GET_REPO.f(_("{module} 的仓库信息查询异常").format(module=module))
        else:
            return Response(data)
