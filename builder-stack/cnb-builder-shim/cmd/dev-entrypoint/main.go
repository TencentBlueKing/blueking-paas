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
	"os"

	"github.com/pkg/errors"

	dc "github.com/TencentBlueking/bkpaas/cnb-builder-shim/internal/devcontainer"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/internal/devcontainer/webserver"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/logging"
)

var logger = logging.Default()

func main() {
	var err error

	if err = buildInit(); err != nil {
		logger.Error(err, "Init Build Runtime Environment Failed")
		os.Exit(1)
	}

	var srv dc.DevWatchServer

	srv, err = webserver.New(&logger)
	if err != nil {
		logger.Error(err, "Start DevContainer Server Failed")
		os.Exit(1)
	}

	exitClean := func() int {
		srv.Clean()
		return 1
	}

	go func() {
		mgr, rErr := dc.NewHotReloadManager()
		if rErr != nil {
			logger.Error(rErr, "New HotReloadManager failed")
			os.Exit(exitClean())
		}

		for {
			event, ok := <-srv.AppReloadEvents()
			if !ok {
				logger.Error(errors.New("event channel closed"), "wait for reload event failed")
				os.Exit(exitClean())
			}

			if rErr = mgr.WriteStatus(event.ID, dc.ReloadProcessing); rErr != nil {
				logger.Error(rErr, "HotReload WriteStatus failed")
				os.Exit(exitClean())
			}

			if event.Rebuild {
				if rErr = mgr.Rebuild(event.ID); rErr != nil {
					mgr.WriteStatus(event.ID, dc.ReloadFailed)
					logger.Error(rErr, "HotReload Rebuild failed")
					continue
				}
			}
			if event.Relaunch {
				if rErr = mgr.Relaunch(event.ID); rErr != nil {
					mgr.WriteStatus(event.ID, dc.ReloadFailed)
					logger.Error(rErr, "HotReload Relaunch failed")
					continue
				}
			}

			mgr.WriteStatus(event.ID, dc.ReloadSuccess)
		}
	}()

	if err = srv.Start(); err != nil {
		logger.Error(err, "Start DevContainer Server Failed")
		os.Exit(exitClean())
	}
}
