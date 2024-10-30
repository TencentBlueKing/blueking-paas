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
	"path/filepath"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/internal/devsandbox/config"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/logging"
)

var _ = Describe("Test setupPlatformEnv", func() {
	var (
		tPlatformDir string
		err          error
	)

	BeforeEach(func() {
		tPlatformDir, err = os.MkdirTemp("", "platform-env")
		Expect(err).To(BeNil())
	})
	AfterEach(func() {
		Expect(os.RemoveAll(tPlatformDir)).To(BeNil())
	})

	It("test write env to file successfully", func() {
		err := setupPlatformEnv(logging.Default(), tPlatformDir, []string{"FOO=flag"})
		Expect(err).To(BeNil())
		content, _ := os.ReadFile(filepath.Join(tPlatformDir, "env", "FOO"))
		Expect(string(content)).To(Equal("flag"))
	})
})

var _ = Describe("Test setupBuildpacksOrder", func() {
	var (
		tCnbDir string
		err     error
	)

	BeforeEach(func() {
		tCnbDir, err = os.MkdirTemp("", "cnb-dir")
		Expect(err).To(BeNil())
	})
	AfterEach(func() {
		Expect(os.RemoveAll(tCnbDir)).To(BeNil())
	})

	It("test write order.toml successfully", func() {
		err := setupBuildpacksOrder(
			logging.Default(),
			"tgz apt https://example.com v;tgz bk-buildpack-python https://example.com v213",
			tCnbDir,
		)
		Expect(err).To(BeNil())

		content, _ := os.ReadFile(filepath.Join(tCnbDir, "order.toml"))
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
		err := setupBuildpacksOrder(
			logging.Default(),
			"tgz apt;tgz bk-buildpack-python https://example.com v213",
			tCnbDir,
		)
		Expect(err).To(BeNil())

		content, _ := os.ReadFile(filepath.Join(tCnbDir, "order.toml"))
		Expect(string(content)).To(Equal(`[[order]]
[[order.group]]
id = 'bk-buildpack-python'
version = 'v213'
`))
	})
})

var _ = Describe("Test InitConfig", func() {
	var err error
	BeforeEach(func() {
		err = config.InitConfig()
		Expect(err).To(BeNil())
	})
	It("test load config with default values", func() {
		sourceConfig := config.G.SourceCode
		Expect(sourceConfig.FetchMethod).To(Equal(config.HTTP))
		Expect(sourceConfig.Workspace).To(Equal("/cnb/devsandbox/src"))
		corsConfig := config.G.Service.CORS
		Expect(corsConfig.AllowOrigins).To(Equal([]string{""}))
		Expect(corsConfig.AllowMethods).To(Equal([]string{"GET", "POST", "PUT", "DELETE", "OPTIONS"}))
		Expect(corsConfig.AllowHeaders).To(Equal([]string{"Origin", "Content-Type", "Authorization"}))
		Expect(corsConfig.ExposeHeaders).To(Equal([]string{"Content-Length"}))
		Expect(corsConfig.AllowCredentials).To(Equal(true))
	})
})
