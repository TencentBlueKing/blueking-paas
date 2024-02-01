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

	dc "github.com/TencentBlueking/bkpaas/cnb-builder-shim/internal/devcontainer"
)

var _ = Describe("Test DeployManager", func() {
	var m *DeployManager
	var tmpAppDir string

	testSrcFilePath := filepath.Join("testdata", "django-helloworld.zip")
	oldAppDir := dc.DefaultAppDir

	BeforeEach(func() {
		m = NewDeployManager()

		tmpAppDir, _ = os.MkdirTemp("", "app")
		dc.DefaultAppDir = tmpAppDir
	})

	AfterEach(func() {
		Expect(os.RemoveAll(tmpAppDir)).To(BeNil())

		dc.DefaultAppDir = oldAppDir
	})

	It("Test deploy", func() {
		result, _ := m.Deploy(testSrcFilePath)

		Expect(len(result.DeployID)).To(Equal(32))
		Expect(result.Status).To(Equal(dc.ReloadProcessing))

		_, err := os.Stat(path.Join(dc.DefaultAppDir, "Procfile"))
		Expect(err).To(BeNil())
	})

	Context("Test get result", func() {
		oldReloadDir := dc.ReloadDir
		oldReloadLogDir := dc.ReloadLogDir

		var rw dc.ResultFileRW

		BeforeEach(func() {
			dc.ReloadDir, _ = os.MkdirTemp("", "reload")
			dc.ReloadLogDir = filepath.Join(dc.ReloadDir, "log")

			rw = dc.ResultFileRW{}
			Expect(rw.Init()).To(BeNil())
		})
		AfterEach(func() {
			Expect(os.RemoveAll(dc.ReloadDir)).To(BeNil())

			dc.ReloadDir = oldReloadDir
			dc.ReloadLogDir = oldReloadLogDir
		})
		It("Test get result", func() {
			reloadID := uuid.NewString()
			rw.WriteStatus(reloadID, dc.ReloadSuccess)
			expectedLog := "build done..."
			os.WriteFile(filepath.Join(dc.ReloadLogDir, reloadID), []byte(expectedLog), 0o644)

			result, _ := m.Result(reloadID, false)
			Expect(result.Status).To(Equal(dc.ReloadSuccess))
			Expect(result.Log).To(Equal(""))

			result, _ = m.Result(reloadID, true)
			Expect(result.Log).To(Equal(expectedLog))
		})
	})
})
