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

package handler

import (
	"bytes"
	"fmt"
	"strings"
	"text/template"

	"github.com/Masterminds/sprig/v3"
	tw "github.com/olekukonko/tablewriter"
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

// DeployOptions 部署时需要使用的配置
type DeployOptions struct {
	AppCode       string
	AppType       string
	Module        string
	DeployEnv     string
	Branch        string
	BkAppManifest map[string]any
}

// DefaultAppDeployResult 普通应用部署结果
type DefaultAppDeployResult struct{}

// String ...
func (r DefaultAppDeployResult) String() string {
	return "xxx"
}

var _ DeployResult = DefaultAppDeployResult{}

// CNativeAppDeployResult 云原生应用部署结果
type CNativeAppDeployResult struct{}

// String ...
func (r CNativeAppDeployResult) String() string {
	return "xxx"
}

var _ DeployResult = CNativeAppDeployResult{}

// DefaultAppDeployRecord 普通应用部署记录
type DefaultAppDeployRecord struct {
	ID       string
	Branch   string
	Version  string
	Operator string
	CostTime string
	Status   string
	StartAt  string
}

// DefaultAppDeployHistory 普通应用部署历史
type DefaultAppDeployHistory struct {
	AppCode   string
	Module    string
	DeployEnv string
	Records   []DefaultAppDeployRecord
}

// String ...
func (h DefaultAppDeployHistory) String() string {
	sb := strings.Builder{}
	sb.WriteString(
		fmt.Sprintf(
			"Application Recent Deploy History (AppCode: %s, Module: %s, Env: %s)\n",
			h.AppCode, h.Module, h.DeployEnv,
		),
	)
	table := tw.NewWriter(&sb)
	table.SetHeader([]string{"Branch", "Version", "Operator", "Cost Time", "Status", "Start At"})

	for _, r := range h.Records {
		table.Rich(
			[]string{r.Branch, r.Version, r.Operator, r.CostTime, r.Status, r.StartAt},
			[]tw.Colors{{}, {}, {}, {}, h.getStatusTextColor(r.Status), {}},
		)
	}
	table.Render()
	return sb.String()
}

// getStatusTextColor 获取状态展示的颜色
func (h DefaultAppDeployHistory) getStatusTextColor(status string) tw.Colors {
	switch status {
	case DeployStatusSuccessful:
		return tw.Colors{tw.FgHiGreenColor}
	case DeployStatusFailed:
		return tw.Colors{tw.FgHiRedColor}
	case DeployStatusInterrupted:
		return tw.Colors{tw.FgHiRedColor}
	case DeployStatusPending:
		return tw.Colors{tw.FgHiYellowColor}
	default:
		return tw.Colors{}
	}
}

var _ DeployHistory = DefaultAppDeployHistory{}

// CNativeAppDeployRecord 云原生应用部署记录
type CNativeAppDeployRecord struct {
	ID       int
	Version  string
	Operator string
	CostTime string
	Status   string
	StartAt  string
}

// CNativeAppDeployHistory 云原生应用部署历史
type CNativeAppDeployHistory struct {
	AppCode   string
	Module    string
	DeployEnv string
	Records   []CNativeAppDeployRecord
}

// String ...
func (h CNativeAppDeployHistory) String() string {
	sb := strings.Builder{}
	sb.WriteString(
		fmt.Sprintf(
			"Application Recent Deploy History (AppCode: %s, Module: %s, Env: %s)\n",
			h.AppCode, h.Module, h.DeployEnv,
		),
	)
	table := tw.NewWriter(&sb)
	table.SetHeader([]string{"Version", "Operator", "Cost Time", "Status", "Start At"})

	for _, r := range h.Records {
		table.Rich(
			[]string{r.Version, r.Operator, r.CostTime, r.Status, r.StartAt},
			[]tw.Colors{{}, {}, {}, h.getStatusTextColor(r.Status), {}},
		)
	}
	table.Render()
	return sb.String()
}

// getStatusTextColor 获取状态展示的颜色
func (h CNativeAppDeployHistory) getStatusTextColor(status string) tw.Colors {
	switch status {
	case DeployStatusReady:
		return tw.Colors{tw.FgHiGreenColor}
	case DeployStatusError:
		return tw.Colors{tw.FgHiRedColor}
	case DeployStatusPending:
		return tw.Colors{tw.FgHiYellowColor}
	case DeployStatusProgressing:
		return tw.Colors{tw.FgHiYellowColor}
	case DeployStatusUnknown:
		return tw.Colors{tw.FgHiYellowColor}
	default:
		return tw.Colors{}
	}
}

var _ DeployHistory = CNativeAppDeployHistory{}
