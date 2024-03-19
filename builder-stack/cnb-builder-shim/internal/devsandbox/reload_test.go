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
	"os/exec"
	"path/filepath"

	"github.com/google/uuid"
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

var _ = Describe("Test HotReloadManager", func() {
	oldReloadDir := ReloadDir
	oldReloadLogDir := ReloadLogDir

	BeforeEach(func() {
		ReloadDir, _ = os.MkdirTemp("", "reload")
		ReloadLogDir = filepath.Join(ReloadDir, "log")
	})
	AfterEach(func() {
		Expect(os.RemoveAll(ReloadDir)).To(BeNil())

		ReloadDir = oldReloadDir
		ReloadLogDir = oldReloadLogDir
	})

	It("Test runCmd", func() {
		mgr, _ := NewHotReloadManager()

		reloadID := uuid.NewString()

		cmd := exec.Command("echo", "hello")
		cmd.Env = os.Environ()
		cmd.Stdin = os.Stdin

		Expect(mgr.runCmd(reloadID, cmd)).To(BeNil())
		log, _ := mgr.ReadLog(reloadID)
		Expect(log).To(Equal("hello\n"))
	})
})

var _ = Describe("Test ReloadResultFile", func() {
	oldReloadDir := ReloadDir
	oldReloadLogDir := ReloadLogDir

	var storage ReloadResultStorage

	BeforeEach(func() {
		ReloadDir, _ = os.MkdirTemp("", "reload")
		ReloadLogDir = filepath.Join(ReloadDir, "log")

		storage, _ = NewReloadResultStorage()
	})
	AfterEach(func() {
		Expect(os.RemoveAll(ReloadDir)).To(BeNil())

		ReloadDir = oldReloadDir
		ReloadLogDir = oldReloadLogDir
	})

	It("Test Read and Write Status", func() {
		reloadID := uuid.NewString()
		expectedStatus := ReloadSuccess
		Expect(storage.WriteStatus(reloadID, ReloadSuccess)).To(BeNil())
		status, _ := storage.ReadStatus(reloadID)
		Expect(status).To(Equal(expectedStatus))
	})

	It("Test Read Log", func() {
		reloadID := uuid.NewString()
		expectedLog := "build done..."

		_ = os.WriteFile(filepath.Join(ReloadLogDir, reloadID), []byte(expectedLog), 0o644)

		log, _ := storage.ReadLog(reloadID)
		Expect(log).To(Equal(expectedLog))
	})
})
