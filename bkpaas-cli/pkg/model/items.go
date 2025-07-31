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

// MinimalApplications 应用简明信息列表
type MinimalApplications struct {
	Total int
	Apps  []AppBasicInfo
}

// Length ...
func (a MinimalApplications) Length() int {
	return a.Total
}

// String ...
func (a MinimalApplications) String() string {
	sb := strings.Builder{}
	sb.WriteString("Application List\n")
	table := tw.NewWriter(&sb)
	table.SetHeader([]string{"#", "Name", "Code"})
	for idx, app := range a.Apps {
		table.Append([]string{fmt.Sprintf("%d", idx+1), app.Name, app.Code})
	}
	table.Render()
	return sb.String()
}

var _ Items = MinimalApplications{}
