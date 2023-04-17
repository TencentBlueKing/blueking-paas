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
)

// EnvBasicInfo 应用部署环境基础信息
type EnvBasicInfo struct {
	Name        string
	ClusterName string
	ClusterID   string
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
Application Basic Information:

Name: {{ .Name }}    Code: {{ .Code }}    Region: {{ .Region }}    Type: {{ .AppType }}

Modules:
  {{- range .Modules }}
  Name: {{ .Name }}    {{ if and .RepoType .RepoURL }}RepoType: {{ .RepoType }}    RepoUrl: {{ .RepoURL }}{{ end }}
  Environments:
    {{- range .Envs }}
    Name: {{ .Name }}    Cluster: {{ .ClusterName }} {{ if .ClusterID }}({{ .ClusterID }}){{ end }}
    {{- end }}
  {{- end }}
{{ end }}
`

	tmpl, err := template.New("").Funcs(sprig.TxtFuncMap()).Parse(tmplStr)
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
