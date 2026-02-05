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
	"os"

	"github.com/samber/lo"
	ctrl "sigs.k8s.io/controller-runtime"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

var _ = Context("test init ProjectConfig", func() {
	It("test load from file", func() {
		var projCfg ProjectConfig
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
platform:
  bkAppCode: "foo"
  bkAppSecret: "bar"
  bkAPIGatewayURL: "https://example.com"
  sentryDSN: "https://sentry.example.com"
  ingressClassName: nginx
`
		file, err := os.CreateTemp("", "")
		Expect(err).NotTo(HaveOccurred())

		_, err = file.Write([]byte(configContent))
		Expect(err).NotTo(HaveOccurred())

		_, err = ctrl.ConfigFile().AtPath(file.Name()).OfKind(&projCfg).Complete()
		Expect(err).NotTo(HaveOccurred())

		// 检测 Health
		Expect(projCfg.Health.HealthProbeBindAddress).To(Equal(":8081"))
		// 检测 Metrics
		Expect(projCfg.Metrics.BindAddress).To(Equal("127.0.0.1:8080"))
		// 检测 webhook
		Expect(projCfg.Webhook.Port).To(Equal(lo.ToPtr(9443)))
		// 检测 leaderElection
		Expect(projCfg.LeaderElection.LeaderElect).To(Equal(lo.ToPtr(true)))
		Expect(projCfg.LeaderElection.ResourceName).To(Equal("e56dbef1.bk.tencent.com"))
		Expect(projCfg.Platform.SentryDSN).To(Equal("https://sentry.example.com"))
		Expect(projCfg.Platform.IngressClassName).To(Equal("nginx"))
		Expect(projCfg.GetIngressClassName()).To(Equal("nginx"))
		Expect(projCfg.Platform.CustomDomainIngressClassName).To(Equal(""))
		Expect(projCfg.GetCustomDomainIngressClassName()).To(Equal("nginx"))
	})

	It("test load from file with customDomainIngressClassName", func() {
		var projCfg ProjectConfig
		configContent := `
apiVersion: paas.bk.tencent.com/v1alpha1
kind: ProjectConfig
metadata:
  name: projectconfig-sample
platform:
  bkAppCode: "foo"
  bkAppSecret: "bar"
  ingressClassName: bk-nginx
  customDomainIngressClassName: nginx
`
		file, err := os.CreateTemp("", "")
		Expect(err).NotTo(HaveOccurred())

		_, err = file.Write([]byte(configContent))
		Expect(err).NotTo(HaveOccurred())

		_, err = ctrl.ConfigFile().AtPath(file.Name()).OfKind(&projCfg).Complete()
		Expect(err).NotTo(HaveOccurred())

		Expect(projCfg.GetIngressClassName()).To(Equal("bk-nginx"))
		Expect(projCfg.GetCustomDomainIngressClassName()).To(Equal("nginx"))
	})

	It("test load from file without any ingressClassName", func() {
		var projCfg ProjectConfig
		configContent := `
apiVersion: paas.bk.tencent.com/v1alpha1
kind: ProjectConfig
metadata:
  name: projectconfig-sample
platform:
  bkAppCode: "foo"
  bkAppSecret: "bar"
`
		file, err := os.CreateTemp("", "")
		Expect(err).NotTo(HaveOccurred())

		_, err = file.Write([]byte(configContent))
		Expect(err).NotTo(HaveOccurred())

		_, err = ctrl.ConfigFile().AtPath(file.Name()).OfKind(&projCfg).Complete()
		Expect(err).NotTo(HaveOccurred())

		Expect(projCfg.GetIngressClassName()).To(Equal(""))
		Expect(projCfg.GetCustomDomainIngressClassName()).To(Equal(""))
	})

	It("test load from file with logVolume config", func() {
		var projCfg ProjectConfig
		configContent := `
apiVersion: paas.bk.tencent.com/v1alpha1
kind: ProjectConfig
metadata:
  name: projectconfig-sample
platform:
  bkAppCode: "foo"
  bkAppSecret: "bar"
logHostPath:
  legacyPath: "/custom/logs"
  mulModulePath: "/custom/v3logs"
`
		file, err := os.CreateTemp("", "")
		Expect(err).NotTo(HaveOccurred())

		_, err = file.Write([]byte(configContent))
		Expect(err).NotTo(HaveOccurred())

		_, err = ctrl.ConfigFile().AtPath(file.Name()).OfKind(&projCfg).Complete()
		Expect(err).NotTo(HaveOccurred())

		Expect(projCfg.LogHostPath.LegacyPath).To(Equal("/custom/logs"))
		Expect(projCfg.LogHostPath.MulModulePath).To(Equal("/custom/v3logs"))
		Expect(projCfg.GetLegacyLogHostPath()).To(Equal("/custom/logs"))
		Expect(projCfg.GetMulModuleLogHostPath()).To(Equal("/custom/v3logs"))
	})

	It("test NewProjectConfig default values", func() {
		projCfg := NewProjectConfig()

		// LogVolume defaults
		Expect(projCfg.GetLegacyLogHostPath()).To(Equal("/data/bkapp/logs"))
		Expect(projCfg.GetMulModuleLogHostPath()).To(Equal("/data/bkapp/v3logs"))

		// Other defaults (existing)
		Expect(projCfg.ResLimits.ProcDefaultCPULimit).To(Equal("4000m"))
		Expect(projCfg.ResLimits.ProcDefaultMemLimit).To(Equal("1024Mi"))
		Expect(projCfg.ResLimits.MaxReplicas).To(Equal(int32(5)))
		Expect(projCfg.MaxProcesses).To(Equal(int32(8)))
	})
})
