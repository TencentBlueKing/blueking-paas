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

package names

import (
	"fmt"
	"strings"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
)

const (
	underscoreReplacer string = "0us0"
	defaultRevision    int64  = 1
)

// PreReleaseHook 生成用于执行 pre-release-hook 的 Pod 名称
func PreReleaseHook(bkapp *paasv1alpha2.BkApp) string {
	revision := defaultRevision
	if rev := bkapp.Status.Revision; rev != nil {
		revision = rev.Revision
	}
	return fmt.Sprintf("pre-release-hook-%d", revision)
}

// Deployment 为应用的不同进程生成 Deployment 资源名称
func Deployment(bkapp *paasv1alpha2.BkApp, process string) string {
	return DNSSafeName(bkapp.GetName() + "--" + process)
}

// Service Return the service name for each process
func Service(bkapp *paasv1alpha2.BkApp, process string) string {
	return DNSSafeName(bkapp.GetName() + "--" + process)
}

// DNSSafeName 通过替换 _ 等特殊字符串，将其变为可安全用于 DNS 域名的值，该算法与 bkpaas
// 中其他逻辑保持一致。
func DNSSafeName(name string) string {
	return strings.ReplaceAll(name, "_", underscoreReplacer)
}
