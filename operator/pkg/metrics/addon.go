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

// Package metrics provides reconcile metrics
package metrics

import "github.com/prometheus/client_golang/prometheus"

// addon reconcile metrics
var (
	GetBkAppInfoFailures = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "bkapp_metrics_get_bkapp_info_failures",
			Help: "Failures when getting blue whale application metadata",
		},
		[]string{MetricLabelBkAppName, MetricLabelNamespace},
	)
	ProvisionAddonInstanceFailures = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "bkapp_metrics_provision_addon_instance_failures",
			Help: "Failures when allocating application enhanced service instances",
		},
		[]string{MetricLabelBkAppName, MetricLabelNamespace},
	)
	QueryAddonSpecsFailures = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "bkapp_metrics_query_addon_specs_failures",
			Help: "Failures when querying application enhanced service specifications",
		},
		[]string{MetricLabelAppCode, MetricLabelModuleName, MetricLabelSvcID},
	)
	QueryAddonSpecsDuration = prometheus.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "bkapp_metrics_query_addon_specs_duration",
			Help:    "Duration of querying application enhanced service specifications",
			Buckets: prometheus.ExponentialBuckets(1, 2, 12),
		},
		[]string{MetricLabelAppCode, MetricLabelModuleName, MetricLabelSvcID},
	)
)
