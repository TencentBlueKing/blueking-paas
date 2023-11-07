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

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
)

const (
	defaultDeployID string = "1"
)

// PreReleaseHook 生成用于执行 pre-release-hook 的 Pod 名称
func PreReleaseHook(bkapp *paasv1alpha2.BkApp) string {
	deployID := bkapp.Status.DeployId
	if deployID == "" {
		deployID = defaultDeployID
	}
	return fmt.Sprintf("pre-rel-%s-%s", bkapp.GetName(), deployID)
}

// Deployment 为应用的不同进程生成 Deployment 资源名称
func Deployment(bkapp *paasv1alpha2.BkApp, process string) string {
	return paasv1alpha2.DNSSafeName(bkapp.GetName() + "--" + process)
}

// Service Return the service name for each process
func Service(bkapp *paasv1alpha2.BkApp, process string) string {
	return paasv1alpha2.DNSSafeName(bkapp.GetName() + "--" + process)
}

// GPA Return the general-pod-autoscaler name for each process
func GPA(bkapp *paasv1alpha2.BkApp, process string) string {
	return paasv1alpha2.DNSSafeName(bkapp.GetName() + "--" + process)
}
