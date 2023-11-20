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

package metric

import (
	"github.com/prometheus/client_golang/prometheus"
)

// metrics ...
var (
	HooksFinishedErrors                 *prometheus.CounterVec
	DeleteResourcesErrors               *prometheus.CounterVec
	DeployActionUpdateBkappStatusErrors *prometheus.CounterVec
	DeleteOutdatedDeployErrors          *prometheus.CounterVec
	DeployExpectedDeployErrors          *prometheus.CounterVec
	GetBkappInfoErrors                  *prometheus.CounterVec
	ProvisionAddonInstanceErrors        *prometheus.CounterVec
	QueryAddonSpecsErrors               *prometheus.CounterVec
	QueryAddonSpecsDuration             *prometheus.HistogramVec
	DeleteOutdatedServiceErrors         *prometheus.CounterVec
	DeployExpectedServiceErrors         *prometheus.CounterVec
	DeleteOutdatedGpaErrors             *prometheus.CounterVec
	DeployExpectedGpaErrors             *prometheus.CounterVec
	AutoscaleUpdateBkappStatusErrors    *prometheus.CounterVec
	AddFinalizerErrors                  *prometheus.CounterVec
	GetBkappErrors                      *prometheus.CounterVec
	BkappReconcileDuration              *prometheus.HistogramVec
)

// InitMetric ...
func InitMetric(register prometheus.Registerer) {
	HooksFinishedErrors = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "bkapp_metrics_hooks_finished_errors",
			Help: "Finalizer errors (failures) when checking if all Hooks are completed",
		},
		[]string{"bkappName", "namespace"},
	)
	DeleteResourcesErrors = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "bkapp_metrics_delete_resources_errors",
			Help: "Finalizer errors (failures) when delete resources (hookspod, service)",
		},
		[]string{"bkappName", "namespace"},
	)
	DeployActionUpdateBkappStatusErrors = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "bkapp_metrics_deploy_action_update_bkapp_status_errors",
			Help: "DeployAction errors when updating bkapp status",
		},
		[]string{"bkappName", "namespace", "deployID"},
	)
	DeleteOutdatedDeployErrors = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "bkapp_metrics_delete_outdated_deploy_errors",
			Help: "Errors when deleting outdated deploy",
		},
		[]string{"bkappName", "namespace", "deployName"},
	)
	DeployExpectedDeployErrors = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "bkapp_metrics_deploy_expected_deploy_errors",
			Help: "Errors when deploying expected deploy",
		},
		[]string{"bkappName", "namespace", "deployName"},
	)
	GetBkappInfoErrors = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "bkapp_metrics_get_bkapp_info_errors",
			Help: "Errors when getting blue whale application metadata",
		},
		[]string{"bkappName", "namespace"},
	)
	ProvisionAddonInstanceErrors = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "bkapp_metrics_provision_addon_Instance_errors",
			Help: "Errors when allocating application enhanced service instances",
		},
		[]string{"bkappName", "namespace"},
	)
	QueryAddonSpecsErrors = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "bkapp_metrics_query_addon_specs_errors",
			Help: "Errors when querying application enhanced service specifications",
		},
		[]string{"appCode", "moduleName", "svcID"},
	)
	QueryAddonSpecsDuration = prometheus.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "bkapp_metrics_query_addon_specs_duration",
			Help:    "Duration of querying application enhanced service specifications",
			Buckets: prometheus.ExponentialBuckets(1, 2, 12),
		},
		[]string{"appCode", "moduleName", "svcID"},
	)
	DeleteOutdatedServiceErrors = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "bkapp_metrics_delete_outdated_service_errors",
			Help: "Errors when deleting outdated services",
		},
		[]string{"bkappName", "namespace", "svcName"},
	)
	DeployExpectedServiceErrors = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "bkapp_metrics_deploy_expected_service_errors",
			Help: "Errors when deploying expected services",
		},
		[]string{"bkappName", "namespace", "svcName"},
	)
	DeleteOutdatedGpaErrors = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "bkapp_metrics_delete_outdated_gpa_errors",
			Help: "Errors when deleting outdated gpa",
		},
		[]string{"bkappName", "namespace", "gpaName"},
	)
	DeployExpectedGpaErrors = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "bkapp_metrics_deploy_expected_gpa_errors",
			Help: "Errors when deploying expected gpa",
		},
		[]string{"bkappName", "namespace", "gpaName"},
	)

	AutoscaleUpdateBkappStatusErrors = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "bkapp_metrics_autoscale_update_bkapp_status_errors",
			Help: "Errors when AutoScaler updates bkapp status",
		},
		[]string{"bkappName", "namespace"},
	)

	AddFinalizerErrors = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "bkapp_metrics_add_finalizer_errors",
			Help: "Errors when AddFinalizer",
		},
		[]string{"bkappName", "namespace"},
	)

	GetBkappErrors = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "bkapp_metrics_get_bkapp_errors",
			Help: "Errors when GetBkapp",
		},
		[]string{"bkappName", "namespace"},
	)

	BkappReconcileDuration = prometheus.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "bkapp_metrics_bkapp_reconcile_duration",
			Help:    "Duration of bkapp reconcile",
			Buckets: prometheus.ExponentialBuckets(1, 2, 12),
		},
		[]string{"bkappName", "namespace"},
	)

	register.MustRegister(HooksFinishedErrors)
	register.MustRegister(DeleteResourcesErrors)
	register.MustRegister(DeployActionUpdateBkappStatusErrors)
	register.MustRegister(DeleteOutdatedDeployErrors)
	register.MustRegister(DeployExpectedDeployErrors)
	register.MustRegister(GetBkappInfoErrors)
	register.MustRegister(ProvisionAddonInstanceErrors)
	register.MustRegister(QueryAddonSpecsErrors)
	register.MustRegister(QueryAddonSpecsDuration)
	register.MustRegister(DeleteOutdatedServiceErrors)
	register.MustRegister(DeployExpectedServiceErrors)
	register.MustRegister(DeleteOutdatedGpaErrors)
	register.MustRegister(DeployExpectedGpaErrors)
	register.MustRegister(AutoscaleUpdateBkappStatusErrors)
	register.MustRegister(AddFinalizerErrors)
	register.MustRegister(GetBkappErrors)
	register.MustRegister(BkappReconcileDuration)
}
