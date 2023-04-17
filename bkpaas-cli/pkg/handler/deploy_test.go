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

package handler_test

import (
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/TencentBlueKing/blueking-paas/client/pkg/apiresources"
	"github.com/TencentBlueKing/blueking-paas/client/pkg/config"
	"github.com/TencentBlueKing/blueking-paas/client/pkg/handler"
	"github.com/TencentBlueKing/blueking-paas/client/pkg/model"
)

var _ = Describe("TestDefaultAppDeployer", func() {
	deployer := handler.DefaultAppDeployer{}
	deployOpts := model.DeployOptions{
		AppCode:   "default-app-1",
		AppType:   "default",
		Module:    "default",
		DeployEnv: "stag",
		Branch:    "master",
	}

	BeforeEach(func() {
		config.LoadMockedConfig()
		apiresources.DefaultRequester = &apiresources.MockedRequester{}
	})

	It("TestExec", func() {
		_, err := deployer.Exec(deployOpts)
		Expect(err).To(BeNil())
	})

	It("TestGetResult", func() {
		result, err := deployer.GetResult(deployOpts)
		Expect(err).To(BeNil())
		Expect(result.IsStable()).To(BeTrue())
		Expect(result.String()).To(ContainSubstring("How to fix Procfile"))
		Expect(result.String()).To(ContainSubstring("Open developer center for more details"))
	})

	It("TestGetHistory", func() {
		history, err := deployer.GetHistory(deployOpts)
		Expect(err).To(BeNil())
		Expect(history.Length()).To(Equal(2))
		Expect(history.Latest()).ToNot(Equal(nil))
		Expect(history.String()).ToNot(Equal(""))
	})
})

var _ = Describe("TestCNativeAppDeployer", func() {
	deployer := handler.CNativeAppDeployer{}
	deployOpts := model.DeployOptions{
		AppCode:   "cnative-app-1",
		AppType:   "default",
		Module:    "default",
		DeployEnv: "stag",
		BkAppManifest: map[string]any{
			"apiVersion": "paas.bk.tencent.com/v1alpha1",
			"kind":       "BkApp",
			"metadata": map[string]any{
				"name": "cnative-app-1",
			},
			"spec": map[string]any{
				"processes": []any{
					map[string]any{
						"name":       "web",
						"image":      "strm/helloworld-http",
						"targetPort": 80,
						"replicas":   2,
					},
				},
			},
		},
	}

	BeforeEach(func() {
		config.LoadMockedConfig()
		apiresources.DefaultRequester = &apiresources.MockedRequester{}
	})

	It("TestExec", func() {
		_, err := deployer.Exec(deployOpts)
		Expect(err).To(BeNil())
	})

	It("TestGetResult", func() {
		result, err := deployer.GetResult(deployOpts)
		Expect(err).To(BeNil())
		Expect(result.IsStable()).To(BeTrue())
		Expect(result.String()).To(ContainSubstring("Conditions:"))
		// 成功部署云原生应用不会包含事件信息
		Expect(result.String()).ToNot(ContainSubstring("Events:"))
	})

	It("TestGetHistory", func() {
		history, err := deployer.GetHistory(deployOpts)
		Expect(err).To(BeNil())
		Expect(history.Length()).To(Equal(2))
		Expect(history.Latest()).ToNot(Equal(nil))
		Expect(history.String()).ToNot(Equal(""))
	})
})
