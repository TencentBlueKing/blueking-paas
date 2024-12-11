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

package main

import (
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/internal/devsandbox/webserver"
	"os"

	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/internal/devsandbox"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/internal/devsandbox/config"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/logging"
)

var logger = logging.Default()

func main() {
	if err := buildInit(); err != nil {
		logger.Error(err, "Init Build Runtime Environment Failed")
		os.Exit(1)
	}

	if err := config.InitConfig(); err != nil {
		logger.Error(err, "Init config failed")
		os.Exit(1)
	}

	if err := initializeSourceCode(); err != nil {
		logger.Error(err, "Initialize source code failed")
		os.Exit(1)
	}

	runDevContainerServer()
}

func runDevContainerServer() {
	var srv devsandbox.DevWatchServer

	srv, err := webserver.New(&logger)
	if err != nil {
		logger.Error(err, "Start DevContainer Server Failed")
		os.Exit(1)
	}

	go func() {
		mgr, mgrErr := devsandbox.NewHotReloadManager()
		if mgrErr != nil {
			logger.Error(mgrErr, "New HotReloadManager failed")
			os.Exit(1)
		}

		for {
			event, readErr := srv.ReadReloadEvent()
			if readErr != nil {
				logger.Error(readErr, "wait for reload event failed")
				os.Exit(1)
			}

			if writeErr := mgr.WriteStatus(event.ID, devsandbox.ReloadProcessing); writeErr != nil {
				logger.Error(writeErr, "HotReload WriteStatus failed")
				os.Exit(1)
			}

			if event.Rebuild {
				if innerErr := mgr.Rebuild(event.ID); innerErr != nil {
					_ = mgr.WriteStatus(event.ID, devsandbox.ReloadFailed)
					logger.Error(innerErr, "HotReload Rebuild failed")
					continue
				}
			}
			if event.Relaunch {
				if innerErr := mgr.Relaunch(event.ID); innerErr != nil {
					_ = mgr.WriteStatus(event.ID, devsandbox.ReloadFailed)
					logger.Error(innerErr, "HotReload Relaunch failed")
					continue
				}
			}

			_ = mgr.WriteStatus(event.ID, devsandbox.ReloadSuccess)
		}
	}()

	if err = srv.Start(); err != nil {
		logger.Error(err, "Start Server Failed")
		os.Exit(1)
	}
}
