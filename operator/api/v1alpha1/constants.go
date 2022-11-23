/*
 * Tencent is pleased to support the open source community by making
 * 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
 * Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 *	http://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under
 * the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 * either express or implied. See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * We undertake not to change the open source license (MIT license) applicable
 * to the current version of the project delivered to anyone in the future.
 */

package v1alpha1

import (
	"time"

	"github.com/samber/lo"
)

// 默认值相关常量
const (
	// ProcDefaultTargetPort 进程服务默认端口
	ProcDefaultTargetPort int32 = 5000

	// WebProcName 表示 web 进程名称
	WebProcName = "web"
)

// ReplicasOne 副本数 1, 用于替换测试程序内的魔数
var ReplicasOne = lo.ToPtr(int32(1))

// ReplicasTwo 副本数 2, 用于替换测试程序内的魔数
var ReplicasTwo = lo.ToPtr(int32(2))

// App信息
const (
	// BkAppRegionKey 注解中存储 region 的键名
	BkAppRegionKey = "bkapp.paas.bk.tencent.com/region"
	// BkAppNameKey 注解或标签中存储应用名称的键名
	BkAppNameKey = "bkapp.paas.bk.tencent.com/name"
	// BkAppCodeKey 注解中存储应用 ID 的键名
	BkAppCodeKey = "bkapp.paas.bk.tencent.com/code"
	// ModuleNameKey 注解中存储模块名称的键名
	ModuleNameKey = "bkapp.paas.bk.tencent.com/module-name"
	// EnvironmentKey 注解中存储当前部署环境的键名
	EnvironmentKey = "bkapp.paas.bk.tencent.com/environment"
	// EngineAppNameKey 注解中存储当前 EngineApp 名称的键名
	EngineAppNameKey = "bkapp.paas.bk.tencent.com/engine-app-name"
)

// 平台相关信息
const (
	// HookTypeKey 注解中存储钩子类型的键名
	HookTypeKey = "bkapp.paas.bk.tencent.com/hook-type"
	// ProcessNameKey 注解或标签中存储进程名称的键名
	ProcessNameKey = "bkapp.paas.bk.tencent.com/process-name"
	// AddonsAnnoKey 注解中存储当前应用依赖的增强服务列表
	AddonsAnnoKey = "bkapp.paas.bk.tencent.com/addons"
	// AccessControlAnnoKey 注解中存储当前应用是否启用白名单功能的键名
	AccessControlAnnoKey = "bkapp.paas.bk.tencent.com/access-control"
	// ImageCredentialsRefAnnoKey 注解中存储镜像凭证引用的键名
	ImageCredentialsRefAnnoKey = "bkapp.paas.bk.tencent.com/image-credentials"
	// DeployIDAnnoKey 注解中存储 bkpaas 部署ID的键名
	DeployIDAnnoKey = "bkapp.paas.bk.tencent.com/bkpaas-deploy-id"
)

const (
	// RevisionAnnoKey 注解中存储当前版本信息的键名
	RevisionAnnoKey = "bkapp.paas.bk.tencent.com/revision"
	// ResourceTypeKey 注解中存储资源类型的键名
	ResourceTypeKey = "bkapp.paas.bk.tencent.com/resource-type"
)

const (
	// DefaultRequeueAfter 调和循环默认的间隔
	DefaultRequeueAfter = time.Second * 3

	// WorkloadOwnerKey 是 kubebuilder cache 用来存储 OwnerReference 主从关联关系的索引键
	WorkloadOwnerKey = ".metadata.controller"

	// BkAppFinalizerName BkApp 的 finalizer 标记
	BkAppFinalizerName = "bkapp.paas.bk.tencent.com/finalizer"
	// DGroupMappingFinalizerName is the name of DomainGroupMapping finalizer
	DGroupMappingFinalizerName = "domain-group-mapping.paas.bk.tencent.com/finalizer"

	// DefaultImagePullSecretName 平台默认的 pullImageSecret 名称
	DefaultImagePullSecretName = "bkapp-dockerconfigjson"
)
