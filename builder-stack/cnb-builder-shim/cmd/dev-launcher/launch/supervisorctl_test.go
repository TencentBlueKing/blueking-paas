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

package launch

import (
	"fmt"
	"os"
	"path/filepath"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/appdesc"
)

var _ = Describe("Test supervisorctl", func() {
	var ctl *SupervisorCtl

	oldDir := supervisorDir
	oldConfFilePath := confFilePath

	BeforeEach(func() {
		supervisorDir, _ = os.MkdirTemp("", "supervisor")
		confFilePath = filepath.Join(supervisorDir, "dev.conf")

		ctl = NewSupervisorCtl()
	})
	AfterEach(func() {
		Expect(os.RemoveAll(supervisorDir)).To(BeNil())

		supervisorDir = oldDir
		confFilePath = oldConfFilePath
	})

	DescribeTable("Test refreshConf", func(conf *SupervisorConf, expectedConfContent string) {
		Expect(ctl.refreshConf(conf)).To(BeNil())

		content, _ := os.ReadFile(confFilePath)
		Expect(string(content)).To(Equal(expectedConfContent))
	}, Entry("with env_variables", MakeSupervisorConf(
		[]Process{
			{ProcType: "web", CommandPath: "/cnb/processes/web"},
			{ProcType: "worker", CommandPath: "/cnb/processes/worker"},
		},
	), fmt.Sprintf(`[unix_http_server]
file = %[1]s/supervisor.sock

[supervisorctl]
serverurl = unix://%[1]s/supervisor.sock

[supervisord]
pidfile = %[1]s/supervisord.pid
logfile = %[1]s/log/supervisord.log

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[program:web]
command = /cnb/processes/web
stdout_logfile = %[1]s/log/web.log
redirect_stderr = true

[program:worker]
command = /cnb/processes/worker
stdout_logfile = %[1]s/log/worker.log
redirect_stderr = true
`, supervisorDir)),
		Entry("without env_variables", MakeSupervisorConf(
			[]Process{
				{ProcType: "web", CommandPath: "/cnb/processes/web"},
				{ProcType: "worker", CommandPath: "/cnb/processes/worker"},
			},
			[]appdesc.Env{{"DJANGO_SETTINGS_MODULE", "settings"}, {"WHITENOISE_STATIC_PREFIX", "/static/"}}...,
		), fmt.Sprintf(`[unix_http_server]
file = %[1]s/supervisor.sock

[supervisorctl]
serverurl = unix://%[1]s/supervisor.sock

[supervisord]
pidfile = %[1]s/supervisord.pid
logfile = %[1]s/log/supervisord.log
environment = DJANGO_SETTINGS_MODULE="settings",WHITENOISE_STATIC_PREFIX="/static/"

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[program:web]
command = /cnb/processes/web
stdout_logfile = %[1]s/log/web.log
redirect_stderr = true

[program:worker]
command = /cnb/processes/worker
stdout_logfile = %[1]s/log/worker.log
redirect_stderr = true
`, supervisorDir)))
})
