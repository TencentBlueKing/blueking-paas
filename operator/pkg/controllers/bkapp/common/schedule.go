/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
 * Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 *     http://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under
 * the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 * either express or implied. See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * We undertake not to change the open source license (MIT license) applicable
 * to the current version of the project delivered to anyone in the future.
 */

package common

import (
	corev1 "k8s.io/api/core/v1"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
)

// BuildNodeSelector builds the node selector for a BkApp by merging user-defined
// selectors with egress-related selectors. User-defined selectors take precedence.
func BuildNodeSelector(app *paasv1alpha2.BkApp) map[string]string {
	result := make(map[string]string)

	// 1. apply egress node selector if exists
	if egressSelector := buildEgressNodeSelector(app); egressSelector != nil {
		for k, v := range egressSelector {
			result[k] = v
		}
	}

	// 2. apply user-defined node selector (no conflict with egress NodeSelector)
	if app.Spec.Schedule != nil && app.Spec.Schedule.NodeSelector != nil {
		for k, v := range app.Spec.Schedule.NodeSelector {
			result[k] = v
		}
	}

	if len(result) == 0 {
		return nil
	}
	return result
}

// buildEgressNodeSelector build the node selector from egress config
func buildEgressNodeSelector(app *paasv1alpha2.BkApp) map[string]string {
	if egressClusterStateName, ok := app.Annotations[paasv1alpha2.EgressClusterStateNameAnnoKey]; ok {
		return map[string]string{egressClusterStateName: "1"}
	}
	return nil
}

// BuildTolerations returns the tolerations configured in the BkApp spec.
func BuildTolerations(app *paasv1alpha2.BkApp) []corev1.Toleration {
	if app.Spec.Schedule == nil {
		return nil
	}
	return app.Spec.Schedule.Tolerations
}
