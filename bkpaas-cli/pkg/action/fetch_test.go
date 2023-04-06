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

package action_test

import (
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/TencentBlueKing/blueking-paas/client/pkg/action"
	"github.com/TencentBlueKing/blueking-paas/client/pkg/apiresources"
)

var _ = Describe("TestFetch", func() {
	BeforeEach(func() {
		apiresources.DefaultRequester = &apiresources.MockedRequester{}
	})

	It("TestAppBasicInfoViewer", func() {
		excepted := map[string]any{
			"code":    "test-code",
			"name":    "test-app",
			"region":  "默认版",
			"appType": "default",
			"modules": []map[string]any{
				{
					"name":     "default",
					"repoType": "Opensource Community Github",
					"repoUrl":  "https://github.com/octocat/Hello-World.git",
					"envs": []map[string]any{
						{
							"name":        "stag",
							"clusterName": "default",
							"clusterId":   "BCS-K8S-12345",
						},
						{
							"name":        "prod",
							"clusterName": "dev",
							"clusterId":   "",
						},
					},
				},
			},
		}

		viewer := action.NewBasicInfoViewer()
		info, err := viewer.Fetch("test-code")
		Expect(info).To(Equal(excepted))
		Expect(err).To(BeNil())

		_, err = viewer.Render(info)
		Expect(err).To(BeNil())
	})
})
