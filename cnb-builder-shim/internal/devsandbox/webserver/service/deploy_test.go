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

package service

import (
	"os"
	"path"
	"path/filepath"

	"github.com/google/uuid"
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/internal/devsandbox"
)

var _ = Describe("Test DeployManager", func() {
	var m *DeployManager
	var tmpAppDir string

	testSrcFilePath := filepath.Join("testdata", "helloworld")
	oldAppDir := devsandbox.DefaultAppDir

	BeforeEach(func() {
		m = NewDeployManager()

		tmpAppDir, _ = os.MkdirTemp("", "app")
		// 创建隐藏目录
		Expect(os.MkdirAll(path.Join(tmpAppDir, ".heroku"), 0o755)).To(BeNil())

		devsandbox.DefaultAppDir = tmpAppDir
	})

	AfterEach(func() {
		Expect(os.RemoveAll(tmpAppDir)).To(BeNil())

		devsandbox.DefaultAppDir = oldAppDir
	})

	Describe("Test deploy", func() {
		It("test deploy", func() {
			result, err := m.Deploy(testSrcFilePath)
			Expect(err).To(BeNil())

			Expect(len(result.DeployID)).To(Equal(32))
			Expect(result.Status).To(Equal(devsandbox.ReloadProcessing))

			_, err = os.Stat(path.Join(devsandbox.DefaultAppDir, "Procfile"))
			Expect(err).To(BeNil())

			// 验证隐藏目录不会被覆盖(删除)
			_, err = os.Stat(path.Join(devsandbox.DefaultAppDir, ".heroku"))
			Expect(err).To(BeNil())
		})
	})

	Describe("Test get result", func() {
		oldReloadDir := devsandbox.ReloadDir
		oldReloadLogDir := devsandbox.ReloadLogDir

		var storage devsandbox.ReloadResultStorage

		BeforeEach(func() {
			devsandbox.ReloadDir, _ = os.MkdirTemp("", "reload")
			devsandbox.ReloadLogDir = filepath.Join(devsandbox.ReloadDir, "log")

			storage, _ = devsandbox.NewReloadResultStorage()
		})
		AfterEach(func() {
			Expect(os.RemoveAll(devsandbox.ReloadDir)).To(BeNil())

			devsandbox.ReloadDir = oldReloadDir
			devsandbox.ReloadLogDir = oldReloadLogDir
		})
		It("Test get result", func() {
			reloadID := uuid.NewString()
			_ = storage.WriteStatus(reloadID, devsandbox.ReloadSuccess)
			expectedLog := "build done..."
			_ = os.WriteFile(filepath.Join(devsandbox.ReloadLogDir, reloadID), []byte(expectedLog), 0o644)

			result, _ := m.Result(reloadID, false)
			Expect(result.Status).To(Equal(devsandbox.ReloadSuccess))
			Expect(result.Log).To(Equal(""))

			result, _ = m.Result(reloadID, true)
			Expect(result.Log).To(Equal(expectedLog))
		})
	})
})

var _ = Describe("Test GetAppLogs", func() {
	var err error
	var logPath string
	var celeryLogPath string
	var mysqlLogPath string
	BeforeEach(func() {
		logPath, err = os.MkdirTemp("", "log_test")
		Expect(err).To(BeNil())
		celeryLogPath = filepath.Join(logPath, "celery.log")
		mysqlLogPath = filepath.Join(logPath, "mysql.log")
		logContent1 := "value1\nvalue2\n"
		logContent2 := "value3\nvalue4\n"
		err := os.WriteFile(celeryLogPath, []byte(logContent1), 0644)
		Expect(err).To(BeNil())
		err = os.WriteFile(mysqlLogPath, []byte(logContent2), 0644)
		Expect(err).To(BeNil())
	})
	AfterEach(func() {
		Expect(os.RemoveAll(logPath)).To(BeNil())
	})
	Describe("Test GetAppLogs", func() {
		It("test lines < logs", func() {
			logs, err := GetAppLogs(logPath, 1)
			Expect(err).To(BeNil())
			Expect(len(logs["celery"])).To(Equal(1))
			Expect(logs["celery"]).To(Equal([]string{"value2"}))
			Expect(len(logs["mysql"])).To(Equal(1))
			Expect(logs["mysql"]).To(Equal([]string{"value4"}))
		})
		It("test lines > logs", func() {
			logs, err := GetAppLogs(logPath, 5)
			Expect(err).To(BeNil())
			Expect(len(logs["celery"])).To(Equal(2))
			Expect(logs["celery"]).To(Equal([]string{"value1", "value2"}))
			Expect(len(logs["mysql"])).To(Equal(2))
			Expect(logs["mysql"]).To(Equal([]string{"value3", "value4"}))
		})
		It("logFile does not exist", func() {
			logs, err := GetAppLogs("", 5)
			Expect(err).To(BeNil())
			Expect(logs).To(BeNil())
		})
	})
})
