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

package v1alpha1

import (
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

// AddonsAnnoKey , BkApp 资源中用于保存增强服务相关信息的 annotation 键名
const AddonsAnnoKey = "bkapp.paas.bk.tencent.com/addons"

// DGroupMappingFinalizerName is the name of DomainGroupMapping finalizer
const DGroupMappingFinalizerName = "domain-group-mapping.paas.bk.tencent.com/finalizer"

// AllowedDomainGroupMappingRefKinds 允许被 DomainGroupMapping 引用的资源类型
var AllowedDomainGroupMappingRefKinds = []string{KindBkApp}

const (
	// SourceTypeSubDomain means domain was allocated by platform, apps are
	// distinguished by subdomains
	SourceTypeSubDomain = "subdomain"

	// SourceTypeSubPath means domain was allocated by platform, apps are
	// distinguished by sub-paths, share a single root domain.
	SourceTypeSubPath = "subpath"

	// SourceTypeCustom means domain was created by user
	SourceTypeCustom = "custom"
)

// AllowedSourceTypes 允许使用的 SourceType
var AllowedSourceTypes = []string{SourceTypeSubDomain, SourceTypeSubPath, SourceTypeCustom}
