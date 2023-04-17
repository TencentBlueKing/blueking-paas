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

	tw "github.com/olekukonko/tablewriter"
)

// AppDeployRecord 应用部署记录
type AppDeployRecord struct {
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
	Total     int
	Records   []AppDeployRecord
}

// Length ...
func (h DefaultAppDeployHistory) Length() int {
	return h.Total
}

// Latest ...
func (h DefaultAppDeployHistory) Latest() *AppDeployRecord {
	if h.Total == 0 {
		return nil
	}
	return &h.Records[0]
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

// CNativeAppDeployHistory 云原生应用部署历史
type CNativeAppDeployHistory struct {
	AppCode   string
	Module    string
	DeployEnv string
	Total     int
	Records   []AppDeployRecord
}

// Length ...
func (h CNativeAppDeployHistory) Length() int {
	return h.Total
}

// Latest ...
func (h CNativeAppDeployHistory) Latest() *AppDeployRecord {
	if h.Total == 0 {
		return nil
	}
	return &h.Records[0]
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
