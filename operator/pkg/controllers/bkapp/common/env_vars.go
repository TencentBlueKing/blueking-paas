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

package common

import (
	"sort"
	"strings"

	"github.com/samber/lo"
	corev1 "k8s.io/api/core/v1"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/envs"
)

// GetAppEnvs will return all EnvVar for the given BkApp, this will include:
// - user defined Configuration in Spec
// - TODO: built-in env vars
func GetAppEnvs(bkapp *paasv1alpha2.BkApp) []corev1.EnvVar {
	// 应用声明的环境变量(优先级最低)
	envs := envs.NewEnvVarsGetter(bkapp).Get()
	// 给所有环境变量排序以获得稳定的结果
	sort.Slice(envs, func(i, j int) bool { return envs[i].Name < envs[j].Name })
	return envs
}

// VarsRenderContext is the context object for rendering variables list
type VarsRenderContext struct {
	// ProcessType is the type of the process, e.g. "web", "worker"
	ProcessType string
}

// RenderAppVars render a list of env variables, it replaces var template with their
// actual values. Only a limited set of vars are supported, including:
//
// - {{bk_var_process_type}} -> real process type
func RenderAppVars(vars []corev1.EnvVar, context VarsRenderContext) []corev1.EnvVar {
	supportedKeySuffixes := []string{"_LOG_NAME_PREFIX", "_PROCESS_TYPE"}

	results := make([]corev1.EnvVar, len(vars))
	for i, v := range vars {
		newValue := v.Value
		// Only do the rendering if the key ends with any supported suffix to prevent
		// unnecessary rendering.
		if lo.SomeBy(supportedKeySuffixes, func(suffix string) bool {
			return strings.HasSuffix(v.Name, suffix)
		}) {
			// TODO: Use other method to replace the variables when more variables are supported
			newValue = strings.Replace(newValue, "{{bk_var_process_type}}", context.ProcessType, -1)
		}

		results[i] = corev1.EnvVar{Name: v.Name, Value: newValue}
	}
	return results
}
