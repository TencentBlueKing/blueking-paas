/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
 * Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 *     http://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under
 * the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 * either express or implied. See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * We undertake not to change the open source license (MIT license) applicable
 * to the current version of the project delivered to anyone in the future.
 */

package devsandbox

import (
	"os"
	"os/user"
	"strconv"

	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/utils"
)

// DefaultLayersDir is the default dir to store bp layers
var DefaultLayersDir = "/layers"

// DefaultAppDir is the default build dir
var DefaultAppDir = utils.EnvOrDefault("CNB_APP_DIR", "/app")

// DefaultAppLogDir is the saas default log dir
var DefaultAppLogDir = utils.EnvOrDefault("CNB_APP_LOG_DIR", "/v3logs")

// AppReloadEvent 事件
type AppReloadEvent struct {
	ID string
	// 是否重新构建应用
	Rebuild bool
	// 是否重启应用
	Relaunch bool
}

// DevWatchServer 是 dev sandbox 中常驻 WatchServer 的接口协议
type DevWatchServer interface {
	// ReadReloadEvent blocking read on AppReloadEvent
	ReadReloadEvent() (AppReloadEvent, error)
	// Start starts the server
	Start() error
}

// GetCNBUID 获取 cnb 用户 uid. 如果用户不存在，返回当前用户 uid
func GetCNBUID() int {
	uidString := utils.EnvOrDefault("CNB_UID", "2000")
	if _, err := user.LookupId(uidString); err != nil {
		return os.Getuid()
	}

	uid, _ := strconv.Atoi(uidString)
	return uid
}

// GetCNBGID 获取 cnb 用户 gid. 如果用户组不存在，返回当前用户组 gid
func GetCNBGID() int {
	gidString := utils.EnvOrDefault("CNB_GID", "2000")
	if _, err := user.LookupGroupId(gidString); err != nil {
		return os.Getgid()
	}

	gid, _ := strconv.Atoi(gidString)
	return gid
}
