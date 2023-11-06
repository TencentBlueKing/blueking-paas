/*
 * TencentBlueKing is pleased to support the open source community by making
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

package v1alpha2

import (
	"time"

	"github.com/samber/lo"
	corev1 "k8s.io/api/core/v1"
)

// 默认值相关常量
const (
	// ProcDefaultTargetPort 进程服务默认端口
	ProcDefaultTargetPort int32 = 5000

	// WebProcName 表示 web 进程名称
	WebProcName = "web"

	// 默认模块名
	DefaultModuleName = "default"
)

// ReplicasOne 副本数 1, 用于替换测试程序内的魔数
var ReplicasOne = lo.ToPtr(int32(1))

// ReplicasTwo 副本数 2, 用于替换测试程序内的魔数
var ReplicasTwo = lo.ToPtr(int32(2))

// BkApp 资源的 annotations 中用来保存特殊信息的键名
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
	// WlAppNameKey 注解中存储当前 EngineApp 名称的键名
	WlAppNameKey = "bkapp.paas.bk.tencent.com/wl-app-name"

	// LegacyProcImageAnnoKey, In API version "v1alpha1", every process can use a different image.
	// This behaviour was changed in "v1alpha2", but we still need to save the legacy images configs
	// in annotations to maintain backward compatibility.
	LegacyProcImageAnnoKey = "bkapp.paas.bk.tencent.com/legacy-proc-image-config"

	// LegacyProcResAnnoKey, In API version "v1alpha1", every process can specify the exact CPU and
	// memory resources. This behaviour was changed in "v1alpha2", but we still need to save the
	// legacy resource configs in annotations to maintain backward compatibility.
	LegacyProcResAnnoKey = "bkapp.paas.bk.tencent.com/legacy-proc-res-config"
)

// 平台相关信息
const (
	// HookTypeKey 注解中存储钩子类型的键名
	HookTypeKey = "bkapp.paas.bk.tencent.com/hook-type"
	// ProcessNameKey 注解或标签中存储进程名称的键名
	ProcessNameKey = "bkapp.paas.bk.tencent.com/process-name"
	// AccessControlAnnoKey 注解中存储当前应用是否启用白名单功能的键名
	AccessControlAnnoKey = "bkapp.paas.bk.tencent.com/access-control"
	// ImageCredentialsRefAnnoKey 注解中存储镜像凭证引用的键名
	ImageCredentialsRefAnnoKey = "bkapp.paas.bk.tencent.com/image-credentials"
	// DeployIDAnnoKey 注解中存储 bkpaas 部署ID的键名
	DeployIDAnnoKey = "bkapp.paas.bk.tencent.com/bkpaas-deploy-id"
	// PaaSAnalysisSiteIDAnnoKey 注解中存储 PA site id 的键名
	PaaSAnalysisSiteIDAnnoKey = "bkapp.paas.bk.tencent.com/paas-analysis-site-id"
)

const (
	// ResourceTypeKey 注解中存储资源类型的键名
	ResourceTypeKey = "bkapp.paas.bk.tencent.com/resource-type"
	// UseCNBAnnoKey 注解中声明镜像类型是否 cnb 的键名
	UseCNBAnnoKey = "bkapp.paas.bk.tencent.com/use-cnb"
	// IngressClassAnnoKey 通过该注解绑定 ingress 的控制器
	IngressClassAnnoKey = "kubernetes.io/ingress.class"
	// DeploySkipUpdateAnnoKey 注解表示当前的进程 Deployment 资源应跳过更新
	DeploySkipUpdateAnnoKey = "bkapp.paas.bk.tencent.com/deployment-skip-update"
	// DeployContentHashAnnoKey 注解保存由 Operator 生成的配置内容哈希值
	DeployContentHashAnnoKey = "bkapp.paas.bk.tencent.com/deployment-content-hash"
)

const (
	// DefaultRequeueAfter 调和循环默认的间隔
	DefaultRequeueAfter = time.Second * 3

	// KubeResOwnerKey 是 kubebuilder cache 用来存储 OwnerReference 主从关联关系的索引键
	KubeResOwnerKey = ".metadata.controller"

	// BkAppFinalizerName BkApp 的 finalizer 标记
	BkAppFinalizerName = "bkapp.paas.bk.tencent.com/finalizer"

	// DefaultImagePullSecretName 平台默认的 pullImageSecret 名称
	DefaultImagePullSecretName = "bkapp-dockerconfigjson"
)

const (
	// GPAComputeByLimitsAnnoKey 在为 GPA 添加注解 compute-by-limits=true 后，
	// 在计算 Utilization 时将根据当前使用量 & limits 来计算目标副本数，否则使用 requests 来计算
	GPAComputeByLimitsAnnoKey = "compute-by-limits"
)

// AllowedScalingPolicies 允许使用的扩缩容策略
var AllowedScalingPolicies = []ScalingPolicy{ScalingPolicyDefault}

// AllowedResQuotaPlans 允许使用的资源配额方案
var AllowedResQuotaPlans = []ResQuotaPlan{
	ResQuotaPlanDefault,
	ResQuotaPlan1C512M,
	ResQuotaPlan2C1G,
	ResQuotaPlan2C2G,
	ResQuotaPlan2C4G,
	ResQuotaPlan4C1G,
	ResQuotaPlan4C2G,
	ResQuotaPlan4C4G,
}

// AllowedImagePullPolicies 允许使用的镜像拉取策略
var AllowedImagePullPolicies = []corev1.PullPolicy{corev1.PullIfNotPresent, corev1.PullAlways, corev1.PullNever}

// FilePathPattern 文件路径正则
const FilePathPattern = `^/([^/\x00]+(/)?)*$`
