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

package supervisord

import (
	"fmt"
	"os"
	"path/filepath"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/appdesc"
)

var _ = Describe("Test process_ctl", func() {
	var supervisorTmpDir string

	oldConfFilePath := confFilePath

	BeforeEach(func() {
		supervisorTmpDir, _ = os.MkdirTemp("", "supervisor")
		confFilePath = filepath.Join(supervisorTmpDir, "dev.conf")
	})
	AfterEach(func() {
		Expect(os.RemoveAll(supervisorTmpDir)).To(BeNil())
		confFilePath = oldConfFilePath
	})

	DescribeTable(
		"Test MakeSupervisorConf with invalid environment variables",
		func(processes []Process, procEnv []appdesc.Env, expectedErrorStr string) {
			_, err := makeSupervisorConf(processes, procEnv...)
			Expect(err.Error()).To(Equal(expectedErrorStr))
		}, Entry(
			"invalid with (%)",
			[]Process{{ProcType: "web", CommandPath: "/cnb/processes/web"}},
			[]appdesc.Env{
				{Name: "FOO", Value: `%abc`},
				{Name: "BAR", Value: `ab%c`},
			},
			`environment variables: FOO, BAR has invalid characters ("%)`,
		),
		Entry(
			"invalid with (%)",
			[]Process{{ProcType: "web", CommandPath: "/cnb/processes/web"}},
			[]appdesc.Env{
				{Name: "FOO", Value: `%abc`},
				{Name: "BAR", Value: `abc`},
			},
			`environment variables: FOO has invalid characters ("%)`,
		),
		Entry(
			`invalid with ("%)`,
			[]Process{{ProcType: "web", CommandPath: "/cnb/processes/web"}},
			[]appdesc.Env{
				{Name: "FOO_TEST", Value: `http://abc.com/cc`},
				{Name: "FOO", Value: `%abc`},
				{Name: "BAR", Value: `ab"c`},
			},
			`environment variables: FOO, BAR has invalid characters ("%)`,
		),
	)

	DescribeTable("Test refreshConf", func(processes []Process, procEnv []appdesc.Env, expectedConfContent string) {
		conf, _ := makeSupervisorConf(processes, procEnv...)
		Expect(refreshConf(conf)).To(BeNil())

		content, _ := os.ReadFile(confFilePath)
		Expect(string(content)).To(Equal(expectedConfContent))
	}, Entry("without env_variables",
		[]Process{
			{ProcType: "web", CommandPath: "/cnb/processes/web"},
			{ProcType: "worker", CommandPath: "/cnb/processes/worker"},
		}, []appdesc.Env{},
		fmt.Sprintf(`[unix_http_server]
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

[inet_http_server]
port=127.0.0.1:%[2]s
`, supervisorDir, rpcPort)),
		Entry("with env_variables",
			[]Process{
				{ProcType: "web", CommandPath: "/cnb/processes/web"},
				{ProcType: "worker", CommandPath: "/cnb/processes/worker"},
			},
			[]appdesc.Env{
				{Name: "DJANGO_SETTINGS_MODULE", Value: "settings"},
				{Name: "WHITENOISE_STATIC_PREFIX", Value: "/static/"},
			}, fmt.Sprintf(`[unix_http_server]
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

[inet_http_server]
port=127.0.0.1:%[2]s
`, supervisorDir, rpcPort)))
})
