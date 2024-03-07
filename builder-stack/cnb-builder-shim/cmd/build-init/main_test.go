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
	"fmt"
	"os"
	"path/filepath"
	"testing"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/logging"
)

func Test(t *testing.T) {
	RegisterFailHandler(Fail)
	RunSpecs(t, "main Suite")
}

var _ = Describe("Test setupPlatformEnv", func() {
	var (
		platformDir string
		err         error
	)

	BeforeEach(func() {
		platformDir, err = os.MkdirTemp("", "platform-env")
		Expect(err).To(BeNil())
	})
	AfterEach(func() {
		Expect(os.RemoveAll(platformDir)).To(BeNil())
	})

	It("test write env to file successfully", func() {
		err := setupPlatformEnv(logging.Default(), platformDir, []string{"FOO=flag"})
		Expect(err).To(BeNil())

		content, _ := os.ReadFile(filepath.Join(platformDir, "env", "FOO"))
		Expect(string(content)).To(Equal("flag"))
	})
	It("test blacklist", func() {
		err := setupPlatformEnv(logging.Default(), platformDir, []string{fmt.Sprintf("%s=flag", OutputImageEnvVarKey)})
		Expect(err).To(BeNil())

		_, err = os.ReadFile(filepath.Join(platformDir, "env", OutputImageEnvVarKey))
		Expect(os.IsNotExist(err)).To(BeTrue())
	})
})

var _ = Describe("Test setupBuildpacksOrder", func() {
	var (
		cnbDir string
		err    error
	)

	BeforeEach(func() {
		cnbDir, err = os.MkdirTemp("", "cnb-dir")
		Expect(err).To(BeNil())
	})
	AfterEach(func() {
		Expect(os.RemoveAll(cnbDir)).To(BeNil())
	})

	It("test write order.toml successfully", func() {
		err := setupBuildpacksOrder(logging.Default(), "tgz apt https://example.com v;tgz bk-buildpack-python https://example.com v213", cnbDir)
		Expect(err).To(BeNil())

		content, _ := os.ReadFile(filepath.Join(cnbDir, "order.toml"))
		Expect(string(content)).To(Equal(`[[order]]
[[order.group]]
id = 'apt'
version = 'v'

[[order.group]]
id = 'bk-buildpack-python'
version = 'v213'
`))
	})

	It("test skip wrong value", func() {
		err := setupBuildpacksOrder(logging.Default(), "tgz apt;tgz bk-buildpack-python https://example.com v213", cnbDir)
		Expect(err).To(BeNil())

		content, _ := os.ReadFile(filepath.Join(cnbDir, "order.toml"))
		Expect(string(content)).To(Equal(`[[order]]
[[order.group]]
id = 'bk-buildpack-python'
version = 'v213'
`))
	})

})
