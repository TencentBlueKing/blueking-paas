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
	"time"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
)

// IncHooksFinishedFailures ...
func IncHooksFinishedFailures(bkapp *paasv1alpha2.BkApp) {
	HooksFinishedFailures.WithLabelValues(bkapp.Name, bkapp.Namespace).Inc()
}

// IncDeleteResourcesFailures ...
func IncDeleteResourcesFailures(bkapp *paasv1alpha2.BkApp) {
	DeleteResourcesFailures.WithLabelValues(bkapp.Name, bkapp.Namespace).Inc()
}

// IncDeployActionUpdateBkappStatusFailures ...
func IncDeployActionUpdateBkappStatusFailures(bkapp *paasv1alpha2.BkApp) {
	DeployActionUpdateBkappStatusFailures.WithLabelValues(bkapp.Name, bkapp.Namespace, bkapp.Status.DeployId).Inc()
}

// IncDeleteOutdatedDeployFailures ...
func IncDeleteOutdatedDeployFailures(bkapp *paasv1alpha2.BkApp, deploymentName string) {
	DeleteOutdatedDeployFailures.WithLabelValues(bkapp.Name, bkapp.Namespace, deploymentName).Inc()
}

// IncDeployExpectedDeployFailures ...
func IncDeployExpectedDeployFailures(bkapp *paasv1alpha2.BkApp, deploymentName string) {
	DeployExpectedDeployFailures.WithLabelValues(bkapp.Name, bkapp.Namespace, deploymentName).Inc()
}

// IncGetBkappInfoFailures ...
func IncGetBkappInfoFailures(bkapp *paasv1alpha2.BkApp) {
	GetBkAppInfoFailures.WithLabelValues(bkapp.Name, bkapp.Namespace).Inc()
}

// IncProvisionAddonInstanceFailures ...
func IncProvisionAddonInstanceFailures(bkapp *paasv1alpha2.BkApp) {
	ProvisionAddonInstanceFailures.WithLabelValues(bkapp.Name, bkapp.Namespace).Inc()
}

// IncQueryAddonSpecsFailures ...
func IncQueryAddonSpecsFailures(appCode, moduleName, svcID string) {
	QueryAddonSpecsFailures.WithLabelValues(appCode, moduleName, svcID).Inc()
}

// ObserveQueryAddonSpecsDuration ...
func ObserveQueryAddonSpecsDuration(appCode, moduleName, svcID string, started time.Time) {
	QueryAddonSpecsDuration.WithLabelValues(appCode, moduleName, svcID).
		Observe(float64(time.Since(started).Milliseconds()))
}

// IncDeleteOutdatedServiceFailures ...
func IncDeleteOutdatedServiceFailures(bkapp *paasv1alpha2.BkApp, svcName string) {
	DeleteOutdatedServiceFailures.WithLabelValues(bkapp.Name, bkapp.Namespace, svcName).Inc()
}

// IncDeployExpectedServiceFailures ...
func IncDeployExpectedServiceFailures(bkapp *paasv1alpha2.BkApp, svcName string) {
	DeployExpectedServiceFailures.WithLabelValues(bkapp.Name, bkapp.Namespace, svcName).Inc()
}

// IncDeleteOutdatedGpaFailures ...
func IncDeleteOutdatedGpaFailures(bkapp *paasv1alpha2.BkApp, gpaName string) {
	DeleteOutdatedGpaFailures.WithLabelValues(bkapp.Name, bkapp.Namespace, gpaName).Inc()
}

// IncDeployExpectedGpaFailures ...
func IncDeployExpectedGpaFailures(bkapp *paasv1alpha2.BkApp, gpaName string) {
	DeployExpectedGpaFailures.WithLabelValues(bkapp.Name, bkapp.Namespace, gpaName).Inc()
}

// IncAutoscaleUpdateBkappStatusFailures ...
func IncAutoscaleUpdateBkappStatusFailures(bkapp *paasv1alpha2.BkApp) {
	AutoscaleUpdateBkappStatusFailures.WithLabelValues(bkapp.Name, bkapp.Namespace).Inc()
}

// IncAddFinalizerFailures ...
func IncAddFinalizerFailures(bkapp *paasv1alpha2.BkApp) {
	AddFinalizerFailures.WithLabelValues(bkapp.Name, bkapp.Namespace).Inc()
}

// IncGetBkappFailures ...
func IncGetBkappFailures(namespace string) {
	GetBkappFailures.WithLabelValues(namespace).Inc()
}

// ObserveBkappReconcileDuration ...
func ObserveBkappReconcileDuration(namespace string, started time.Time) {
	BkappReconcileDuration.WithLabelValues(namespace).
		Observe(float64(time.Since(started).Milliseconds()))
}

// IncDeleteOldestHookFailures ...
func IncDeleteOldestHookFailures(bkapp *paasv1alpha2.BkApp) {
	DeleteOldestHookFailures.WithLabelValues(bkapp.Name, bkapp.Namespace).Inc()
}
