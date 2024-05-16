# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views import View

from paasng.plat_admin.admin42.serializers.runtime import AppBuildPackSLZ, AppSlugBuilderSLZ, AppSlugRunnerSLZ
from paasng.plat_admin.admin42.utils.mixins import GenericTemplateView
from paasng.platform.modules.models import AppBuildPack, AppSlugBuilder, AppSlugRunner

from .forms import AppBuildPackForm, AppSlugBuilderForm, AppSlugRunnerForm


class ViewBuilder:
    error_template = "admin42/error.html"

    def __init__(
        self,
        name=None,
        query_set=None,
        list_template=None,
        list_path=None,
        form_template=None,
        form_cls=None,
        serializer_class=None,
    ):
        self.name = name
        self.query_set = query_set
        self.list_template = list_template
        self.list_path = list_path
        self.form_template = form_template
        self.form_cls = form_cls
        self.serializer_class = serializer_class

    def list_view(self):
        class ListView(GenericTemplateView):
            name = self.name
            queryset = self.query_set
            serializer_class = self.serializer_class
            template_name = self.list_template
            template = self.list_template

            def get_context_data(self, **kwargs):
                if "view" not in kwargs:
                    kwargs["view"] = self

                if self.serializer_class:
                    kwargs["data"] = self.get_serializer(self.get_queryset(), many=True).data
                else:
                    kwargs["data"] = self.get_queryset()

                return kwargs

        return ListView

    def create_view(self):
        class CreateView(View):
            name = self.name
            error_template = self.error_template
            form_cls = self.form_cls
            template = self.form_template
            list_path = self.list_path

            def get(self, request):
                return render(request, self.template, {"form": self.form_cls(), "view": self})

            def perform_create(self, form):
                instance = form.save()
                instance.save()
                return instance

            def post(self, request):
                form = self.form_cls(request.POST, request.FILES)
                if form.is_valid():
                    try:
                        self.perform_create(form)
                    except Exception as e:
                        return render(
                            request,
                            self.error_template,
                            {
                                "message": _("创建失败: %s") % e,
                                "error": e,
                            },
                        )
                    return redirect(reverse_lazy(self.list_path), args=[])
                else:
                    return render(
                        request,
                        self.template,
                        {
                            "form": form,
                        },
                    )

        return CreateView

    def update_view(self):
        class UpdateView(View):
            name = self.name
            error_template = self.error_template
            form_cls = self.form_cls
            template = self.form_template
            list_path = self.list_path
            queryset = self.query_set

            def get_object(self, request):
                return get_object_or_404(self.queryset, pk=request.GET.get("id", ""))

            def get(self, request):
                instance = self.get_object(request)
                return render(
                    request, self.template, {"form": self.form_cls(instance=instance), "id": instance.pk, "view": self}
                )

            def perform_update(self, form):
                instance = form.save()
                instance.save()
                return instance

            def post(self, request):
                instance = self.get_object(request)
                form = self.form_cls(request.POST, request.FILES, instance=instance)
                if form.is_valid():
                    try:
                        self.perform_update(form)
                    except Exception as e:
                        return render(
                            request,
                            self.error_template,
                            {
                                "message": _("更新失败: %s") % e,
                                "error": e,
                            },
                        )
                    return redirect(reverse_lazy(self.list_path), args=[])
                else:
                    return render(
                        request,
                        self.template,
                        {
                            "form": form,
                            "id": instance.pk,
                        },
                    )

        return UpdateView

    def delete_view(self):
        class DeleteView(View):
            error_template = self.error_template
            queryset = self.query_set
            list_path = self.list_path

            def perform_delete(self, query_set):
                instance = get_object_or_404(query_set)
                instance.delete()

            def post(self, request):
                try:
                    self.perform_delete(self.queryset.filter(pk=request.POST.get("id", "")))
                except Exception as e:
                    return render(
                        request,
                        self.error_template,
                        {
                            "message": _("删除失败: %s") % e,
                            "error": e,
                        },
                    )
                return redirect(reverse_lazy(self.list_path), args=[])

        return DeleteView


slugbuilder_viewbuilder = ViewBuilder(
    name="SlugBuilder管理",
    query_set=AppSlugBuilder.objects.order_by("region", "type"),
    list_template="admin42/platformmgr/runtime/slugbuilder_list.html",
    list_path="admin.slugbuilder.list",
    form_template="admin42/platformmgr/runtime/bootstrap_form.html",
    form_cls=AppSlugBuilderForm,
    serializer_class=AppSlugBuilderSLZ,
)
SlugBuilderListView = slugbuilder_viewbuilder.list_view()
SlugBuilderCreateView = slugbuilder_viewbuilder.create_view()
SlugBuilderUpdateView = slugbuilder_viewbuilder.update_view()
SlugBuilderDeleteView = slugbuilder_viewbuilder.delete_view()

slugrunner_viewbuilder = ViewBuilder(
    name="SlugRunner管理",
    query_set=AppSlugRunner.objects.order_by("region", "type"),
    list_template="admin42/platformmgr/runtime/slugrunner_list.html",
    list_path="admin.slugrunner.list",
    form_template="admin42/platformmgr/runtime/bootstrap_form.html",
    form_cls=AppSlugRunnerForm,
    serializer_class=AppSlugRunnerSLZ,
)
SlugRunnerListView = slugrunner_viewbuilder.list_view()
SlugRunnerCreateView = slugrunner_viewbuilder.create_view()
SlugRunnerUpdateView = slugrunner_viewbuilder.update_view()
SlugRunnerDeleteView = slugrunner_viewbuilder.delete_view()

buildpack_viewbuilder = ViewBuilder(
    name="BuildPack管理",
    query_set=AppBuildPack.objects.order_by("region", "type", "language", "version"),
    list_template="admin42/platformmgr/runtime/buildpack_list.html",
    list_path="admin.buildpack.list",
    form_template="admin42/platformmgr/runtime/bootstrap_form.html",
    form_cls=AppBuildPackForm,
    serializer_class=AppBuildPackSLZ,
)
BuildPackListView = buildpack_viewbuilder.list_view()
BuildPackCreateView = buildpack_viewbuilder.create_view()
BuildPackUpdateView = buildpack_viewbuilder.update_view()
BuildPackDeleteView = buildpack_viewbuilder.delete_view()
