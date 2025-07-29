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

// Package cmd provides some helper functions for cobra commands.
package cmd

import (
	"strings"

	"github.com/spf13/cobra"

	"github.com/TencentBlueKing/blueking-paas/client/pkg/utils/console"
)

// DefaultSubCmdRun prints a command's help string to the specified output if no
// arguments (sub-commands) are provided, or a usage error otherwise.
func DefaultSubCmdRun() func(c *cobra.Command, args []string) {
	return func(c *cobra.Command, args []string) {
		RequireNoArgs(args)
		_ = c.Help()
	}
}

// RequireNoArgs exits with a usage error if extra arguments are provided.
func RequireNoArgs(args []string) {
	if len(args) > 0 {
		console.Error("Unknown command: %q", strings.Join(args, " "))
	}
}
