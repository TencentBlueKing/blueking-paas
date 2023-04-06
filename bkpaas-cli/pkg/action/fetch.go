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

package action

import (
	"bytes"
	"text/template"

	"github.com/Masterminds/sprig/v3"
	"github.com/TencentBlueKing/gopkg/mapx"

	"github.com/TencentBlueKing/blueking-paas/client/pkg/apiresources"
)

// 应用基础信息查看
type BasicInfoViewer struct{}

// NewBasicInfoViewer ...
func NewBasicInfoViewer() *BasicInfoViewer {
	return &BasicInfoViewer{}
}

// Fetch 调用 API 获取应用基础信息
func (v *BasicInfoViewer) Fetch(appCode string) (map[string]any, error) {
	appInfo, err := apiresources.DefaultRequester.GetAppInfo(appCode)
	if err != nil {
		return nil, err
	}
	modules := []map[string]any{}
	for _, mod := range mapx.GetList(appInfo, "application.modules") {
		m, _ := mod.(map[string]any)

		// 环境基础信息
		envs := []map[string]any{}
		for envName, clusterInfo := range mapx.GetMap(m, "clusters") {
			envs = append(envs, map[string]any{
				"name":        envName,
				"clusterName": mapx.GetStr(clusterInfo.(map[string]any), "name"),
				"clusterId":   mapx.GetStr(clusterInfo.(map[string]any), "bcs_cluster_id"),
			})
		}

		// 模块基础信息
		modules = append(modules, map[string]any{
			"name":     mapx.GetStr(m, "name"),
			"repoType": mapx.GetStr(m, "repo.display_name"),
			"repoUrl":  mapx.GetStr(m, "repo.repo_url"),
			"envs":     envs,
		})
	}

	return map[string]any{
		"code":    appCode,
		"name":    mapx.GetStr(appInfo, "application.name"),
		"region":  mapx.GetStr(appInfo, "application.region_name"),
		"appType": mapx.GetStr(appInfo, "application.type"),
		"modules": modules,
	}, nil
}

// Render 将应用基础信息渲染为展示用的字符串
func (v *BasicInfoViewer) Render(info map[string]any) (string, error) {
	tmplStr := `
{{ define "AppBasicInfo" -}}
Application Basic Info:

Name: {{ .name }}    Code: {{ .code }}    Region: {{ .region }}    Type: {{ .appType }}

Modules:
  {{- range .modules }}
  Name: {{ .name }}    {{ if and .repoType .repoUrl }}RepoType: {{ .repoType }}    RepoUrl: {{ .repoUrl }}{{ end }}
  Environments:
    {{- range .envs }}
    Name: {{ .name }}    Cluster: {{ .clusterName }} {{ if .clusterId }}({{ .clusterId }}){{ end }}
    {{- end }}
  {{ end }}
{{ end }}
`

	tmpl, err := template.New("").Funcs(sprig.TxtFuncMap()).Parse(tmplStr)
	if err != nil {
		return "", err
	}
	var buf bytes.Buffer
	err = tmpl.ExecuteTemplate(&buf, "AppBasicInfo", info)
	if err != nil {
		return "", err
	}
	return buf.String(), nil
}

var _ Viewer = &BasicInfoViewer{}
