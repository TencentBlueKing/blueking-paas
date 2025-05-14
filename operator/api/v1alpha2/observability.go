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

// Metric is monitor metric config for process services
type Metric struct {
	// Process is the name of process
	Process string `json:"process"`
	// ServiceName is the name of process service
	ServiceName string `json:"serviceName"`
	// Path is the path of metric api
	Path string `json:"path"`
	// Params is the params of metric api
	Params map[string]string `json:"params,omitempty"`
}

// Monitoring is monitor config
type Monitoring struct {
	Metrics []Metric `json:"metrics"`
}

// Observability holds observability config
type Observability struct {
	Monitoring Monitoring `json:"monitoring,omitempty"`
}
