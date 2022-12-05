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

package v1alpha1

import (
	"io/ioutil"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	"github.com/samber/lo"
	ctrl "sigs.k8s.io/controller-runtime"
)

var _ = Context("test init ProjectConfig", func() {
	It("test load from file", func() {
		var projectConfig ProjectConfig
		configContent := `
apiVersion: paas.bk.tencent.com/v1alpha1
kind: ProjectConfig
metadata:
  name: projectconfig-sample
health:
  healthProbeBindAddress: :8081
metrics:
  bindAddress: 127.0.0.1:8080
webhook:
  port: 9443
leaderElection:
  leaderElect: true
  resourceName: e56dbef1.bk.tencent.com
platformConfig:
  bkAppCode: "foo"
  bkAppSecret: "bar"
  bkAPIGatewayURL: "https://example.com"
`
		file, err := ioutil.TempFile("", "")
		Expect(err).NotTo(HaveOccurred())

		_, err = file.Write([]byte(configContent))
		Expect(err).NotTo(HaveOccurred())

		_, err = ctrl.ConfigFile().AtPath(file.Name()).OfKind(&projectConfig).Complete()
		Expect(err).NotTo(HaveOccurred())

		// 检测 Health
		Expect(projectConfig.Health.HealthProbeBindAddress).To(Equal(":8081"))
		// 检测 Metrics
		Expect(projectConfig.Metrics.BindAddress).To(Equal("127.0.0.1:8080"))
		// 检测 webhook
		Expect(projectConfig.Webhook.Port).To(Equal(lo.ToPtr(9443)))
		// 检测 leaderElection
		Expect(projectConfig.LeaderElection.LeaderElect).To(Equal(lo.ToPtr(true)))
		Expect(projectConfig.LeaderElection.ResourceName).To(Equal("e56dbef1.bk.tencent.com"))
		// 检测 platformConfig
		Expect(projectConfig.PlatformConfig.BkAppCode).To(Equal("foo"))
		Expect(projectConfig.PlatformConfig.BkAppSecret).To(Equal("bar"))
		Expect(projectConfig.PlatformConfig.BkAPIGatewayURL).To(Equal("https://example.com"))
	})
})
