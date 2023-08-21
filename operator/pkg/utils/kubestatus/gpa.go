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

package kubestatus

import (
	corev1 "k8s.io/api/core/v1"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"

	autoscaling "github.com/Tencent/bk-bcs/bcs-runtime/bcs-k8s/bcs-component/bcs-general-pod-autoscaler/pkg/apis/autoscaling/v1alpha1"
)

// GenGPAHealthStatus check if the GPA is healthy
// For a deployment:
//
//	healthy means the GPA is available, ready to scale workloads with policy.
//	unhealthy means the GPA is failed when reconciled.
func GenGPAHealthStatus(gpa *autoscaling.GeneralPodAutoscaler) *HealthStatus {
	for _, condition := range gpa.Status.Conditions {
		if condition.Status == corev1.ConditionFalse {
			return &HealthStatus{
				Phase:   paasv1alpha2.HealthUnhealthy,
				Reason:  condition.Reason,
				Message: condition.Message,
			}
		}
	}

	return &HealthStatus{
		Phase:   paasv1alpha2.HealthHealthy,
		Reason:  paasv1alpha2.AutoscalingAvailable,
		Message: "",
	}
}
