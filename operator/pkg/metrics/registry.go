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

package metrics

import (
	"github.com/prometheus/client_golang/prometheus"
	"sigs.k8s.io/controller-runtime/pkg/metrics"
)

var collectorGroup = []prometheus.Collector{
	HooksFinishedFailures,
	DeleteResourcesFailures,
	DeployActionUpdateBkappStatusFailures,
	DeleteOutdatedDeployFailures,
	DeployExpectedDeployFailures,
	GetBkAppInfoFailures,
	ProvisionAddonInstanceFailures,
	QueryAddonSpecsFailures,
	QueryAddonSpecsDuration,
	DeleteOutdatedServiceFailures,
	DeployExpectedServiceFailures,
	DeleteOutdatedGpaFailures,
	DeployExpectedGpaFailures,
	AutoscaleUpdateBkappStatusFailures,
	AddFinalizerFailures,
	GetBkappFailures,
	BkappReconcileDuration,
	DeleteOldestHookFailures,
}

func init() {
	// register operator metrics to kubebuilder default register,
	// which can be accessed from the default metrics exposed address "/metrics"
	// and is protected by kube-rbac-proxy
	// see also: https://kubebuilder.io/reference/metrics
	register := metrics.Registry

	for _, collector := range collectorGroup {
		register.MustRegister(collector)
	}
}
