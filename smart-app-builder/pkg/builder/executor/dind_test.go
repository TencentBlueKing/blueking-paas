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

package executor

import (
	"fmt"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/config"
)

var _ = Describe("DindCmdProvider", func() {
	// 设置全局配置
	config.SetGlobalConfig()

	unixSock := fmt.Sprintf("unix://%s", config.G.DaemonSockFile)
	dindCommandProvider := dindCmdProvider{
		execPath: "docker",
	}

	It("StartDaemon", func() {
		cmd := dindCommandProvider.StartDaemon()
		Expect(cmd.Args).To(Equal([]string{""}))
	})

	It("LoadImage", func() {
		cmd := dindCommandProvider.LoadImage("/tmp/test.tar")
		Expect(
			cmd.Args,
		).To(Equal([]string{"docker", "-H", unixSock, "load", "-i", "/tmp/test.tar"}))
	})

	It("SaveImage", func() {
		cmd := dindCommandProvider.SaveImage("test:latest", "/tmp/test.tar")
		Expect(
			cmd.Args,
		).To(Equal([]string{"docker", "-H", unixSock, "save", "-o", "/tmp/test.tar", "test:latest"}))
	})

	It("RunImage", func() {
		cmd := dindCommandProvider.RunImage("test:latest", "echo", "hello")
		Expect(
			cmd.Args,
		).To(Equal([]string{"docker", "-H", unixSock, "run", "echo", "hello", "test:latest"}))
	})
})
