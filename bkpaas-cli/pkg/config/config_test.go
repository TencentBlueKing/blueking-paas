/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
 * Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 *	http://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under
 * the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 * either express or implied. See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * We undertake not to change the open source license (MIT license) applicable
 * to the current version of the project delivered to anyone in the future.
 */

package config_test

import (
	"fmt"
	"os"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/TencentBlueKing/blueking-paas/client/pkg/config"
	"github.com/TencentBlueKing/blueking-paas/client/pkg/utils/pathx"
)

var _ = Describe("TestConfig", func() {
	confFilePath := pathx.GetCurPKGPath() + "/../../etc/conf.yaml"
	config.FilePath = confFilePath

	It("TestLoadConfig", func() {
		conf, err := config.LoadConf(confFilePath)
		Expect(err).Should(BeNil())

		Expect(conf.PaaSApigwUrl).To(Equal("http://bkapi.example.com/api/bkpaas3"))
		Expect(conf.CheckTokenUrl).To(Equal("https://apigw.example.com/auth/check_token/"))
		Expect(conf.PaaSUrl).To(Equal("https://bkpaas3.example.com"))
		Expect(conf.Username).To(Equal("admin"))
		Expect(conf.AccessToken).To(Equal(""))
	})

	It("TestDumpConfig", func() {
		_, err := config.LoadConf(confFilePath)
		Expect(err).Should(BeNil())

		tmpFile, _ := os.CreateTemp("", "")

		config.G.AccessToken = "a_fake_access_token"
		err = config.DumpConf(tmpFile.Name())
		Expect(err).Should(BeNil())

		conf, err := config.LoadConf(tmpFile.Name())
		Expect(err).Should(BeNil())
		Expect(conf.AccessToken).To(Equal("a_fake_access_token"))

		_ = os.Remove(tmpFile.Name())
	})

	It("TestString", func() {
		conf, err := config.LoadConf(confFilePath)
		Expect(err).Should(BeNil())

		excepted := fmt.Sprintf(
			"configFilePath: %s\n\npaasApigwUrl: %s\npaasUrl: %s\ncheckTokenUrl: %s\nusername: %s\naccessToken: [REDACTED]",
			confFilePath,
			"http://bkapi.example.com/api/bkpaas3",
			"https://bkpaas3.example.com",
			"https://apigw.example.com/auth/check_token/",
			"admin",
		)
		Expect(conf.String()).To(Equal(excepted))
	})
})
