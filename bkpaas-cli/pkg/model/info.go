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

package model

import (
	"bytes"
	"text/template"

	"github.com/Masterminds/sprig/v3"
	"github.com/jedib0t/go-pretty/v6/text"
)

// EnvBasicInfo 应用部署环境基础信息
type EnvBasicInfo struct {
	Name    string
	Cluster string
	// TODO 补充访问入口，最近部署情况等信息
}

// ModuleBasicInfo 模块基础信息
type ModuleBasicInfo struct {
	Name     string
	RepoType string
	RepoURL  string
	Envs     []EnvBasicInfo
}

// AppBasicInfo 应用基础信息
type AppBasicInfo struct {
	Code    string
	Name    string
	Region  string
	AppType string
	Modules []ModuleBasicInfo
}

// String ...
func (i AppBasicInfo) String() string {
	tmplStr := `
{{ define "AppBasicInfo" -}}
+-----------------------------------------------------------------------------------------------------+
|                                Application Basic Information                                        |
+------+----------------------------------------------------------------------------------------------+
| Name | {{ pad .Name 15 ' ' }} | Code | {{ pad .Code 15 ' ' }} | Region | {{ pad .Region 15 ' ' }} | Type | {{ pad .AppType 15 ' ' }} |
+------+----------------------------------------------------------------------------------------------+
|                                           Modules                                                   |
+-----------------------------------------------------------------------------------------------------+
{{- range $idx, $mod := .Modules }}
|   {{ $idx }}   | Name     | {{ pad $mod.Name 80 ' ' }} |
{{- if and $mod.RepoType $mod.RepoURL }}
+       +---------------------------------------------------------------------------------------------+
|       | RepoType | {{ pad $mod.RepoType 12 ' ' }} | RepoUrl | {{ pad $mod.RepoURL 55 ' ' }} |
{{- end }}
{{- range $mod.Envs }}
+       +---------------------------------------------------------------------------------------------+
|       | Env      | {{ pad .Name 12 ' ' }} | Cluster | {{ pad .Cluster 55 ' ' }} |
{{- end }}
+-----------------------------------------------------------------------------------------------------+
{{- end }}
{{ end }}
`
	funcMap := sprig.TxtFuncMap()
	funcMap["pad"] = text.Pad
	tmpl, err := template.New("").Funcs(funcMap).Parse(tmplStr)
	if err != nil {
		return err.Error()
	}
	var buf bytes.Buffer
	err = tmpl.ExecuteTemplate(&buf, "AppBasicInfo", i)
	if err != nil {
		return err.Error()
	}
	return buf.String()
}

var _ AppInfo = AppBasicInfo{}
