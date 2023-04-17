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
	"fmt"
	"strings"

	"github.com/fatih/color"
	tw "github.com/olekukonko/tablewriter"
	"github.com/samber/lo"
	"github.com/spf13/cast"

	"github.com/TencentBlueKing/blueking-paas/client/pkg/config"
)

// ErrTip 普通应用部署失败提示
type ErrTip struct {
	Text string
	Link string
}

// DefaultAppDeployResult 普通应用部署结果
type DefaultAppDeployResult struct {
	AppCode   string
	Module    string
	DeployEnv string
	DeployID  string
	Status    string
	Logs      string
	ErrDetail string
	ErrTips   []ErrTip
}

// IsStable ...
func (r DefaultAppDeployResult) IsStable() bool {
	return r.Status == DeployStatusFailed || r.Status == DeployStatusSuccessful || r.Status == DeployStatusInterrupted
}

// String ...
func (r DefaultAppDeployResult) String() string {
	result := fmt.Sprintf("Logs:\n%s\n\n", strings.Trim(r.Logs, "\n"))
	if r.Status == DeployStatusFailed {
		result += color.RedString("Deploy failed, detail: %s\n", r.ErrDetail)
		result += "You can:\n"
		for idx, tip := range r.ErrTips {
			result += fmt.Sprintf("%d: %s: %s\n", idx+1, tip.Text, tip.Link)
		}
	} else if r.Status == DeployStatusInterrupted {
		result += color.YellowString("Deploy interrupted by user.\n")
	} else if r.Status == DeployStatusSuccessful {
		result += color.GreenString("Deploy successful.\n")
	}
	result += fmt.Sprintf(
		"\n↗ Open developer center for more details: %s/developer-center/apps/%s/%s/deploy/%s\n",
		config.G.PaaSUrl, r.AppCode, r.Module, r.DeployEnv,
	)
	return result
}

var _ DeployResult = DefaultAppDeployResult{}

// Condition 云原生应用部署状态信息
type Condition struct {
	Type    string
	Status  string
	Reason  string
	Message string
}

// Event 云原生应用部署事件
type Event struct {
	Name      string
	LastSeen  string
	Component string
	Type      string
	Message   string
	Count     string
}

// CNativeAppDeployResult 云原生应用部署结果
type CNativeAppDeployResult struct {
	AppCode    string
	Module     string
	DeployEnv  string
	Url        string
	Status     string
	Reason     string
	Message    string
	Conditions []Condition
	Events     []Event
}

// IsStable ...
func (r CNativeAppDeployResult) IsStable() bool {
	return r.Status == DeployStatusError || r.Status == DeployStatusReady
}

// String ...
func (r CNativeAppDeployResult) String() string {
	sb := strings.Builder{}
	r.attachConditions(&sb)

	if r.Status == DeployStatusError {
		// 仅失败时候会展示部署事件
		r.attachEvents(&sb)
		// 部署失败提示
		sb.WriteString(color.RedString("Deploy failed: %s -> %s\n", r.Reason, r.Message))
	} else if r.Status == DeployStatusReady {
		// 部署成功提示
		sb.WriteString(color.GreenString("Deploy successful.\n"))
		sb.WriteString(fmt.Sprintf("\n↗ SaaS Home Page: %s\n", r.Url))
	}

	sb.WriteString(
		fmt.Sprintf(
			"\n↗ Open developer center for more details: %s/developer-center/apps/%s/%s/status\n",
			config.G.PaaSUrl, r.AppCode, r.Module,
		),
	)
	return sb.String()
}

// 向输出结果中追加部署状态信息
func (r CNativeAppDeployResult) attachConditions(sb *strings.Builder) {
	sb.WriteString(
		fmt.Sprintf("Deploy Conditions: (Code: %s, Module: %s, Env: %s)\n", r.AppCode, r.Module, r.DeployEnv),
	)
	table := tw.NewWriter(sb)
	table.SetHeader([]string{"Type", "Status", "Reason", "Message"})
	table.SetRowLine(true)

	for _, c := range r.Conditions {
		table.Rich(
			[]string{c.Type, c.Status, c.Reason, c.Message},
			[]tw.Colors{{}, lo.Ternary(cast.ToBool(c.Status), tw.Colors{}, tw.Colors{tw.FgHiRedColor}), {}, {}},
		)
	}
	table.Render()
}

// 向输出结果中追加部署事件信息
func (r CNativeAppDeployResult) attachEvents(sb *strings.Builder) {
	sb.WriteString("Events:\n")
	table := tw.NewWriter(sb)
	table.SetHeader([]string{"LastSeen", "Component", "Type", "Message", "Count"})
	table.SetRowLine(true)
	for _, e := range r.Events {
		// 非普通事件都展示红色
		typeColumColors := lo.Ternary(cast.ToBool(e.Type == "Normal"), tw.Colors{}, tw.Colors{tw.FgHiRedColor})
		table.Rich(
			[]string{e.LastSeen, e.Component, e.Type, e.Message, e.Count},
			[]tw.Colors{{}, {}, typeColumColors, {}, {}},
		)
	}
	table.Render()
}

var _ DeployResult = CNativeAppDeployResult{}
