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

package names

import (
	"fmt"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
)

var _ = Describe("Get resource names", func() {
	var bkapp *paasv1alpha2.BkApp

	BeforeEach(func() {
		bkapp = &paasv1alpha2.BkApp{
			ObjectMeta: metav1.ObjectMeta{
				Name:      "foo-app",
				Namespace: "default",
			},
			Spec: paasv1alpha2.AppSpec{},
		}
	})

	Context("pre-release hook", func() {
		It("No DeployID", func() {
			Expect(PreReleaseHook(bkapp)).To(Equal("pre-rel-foo-app-1"))
		})

		It("Has DeployID", func() {
			deployID := fmt.Sprintf("%d", GinkgoRandomSeed())
			bkapp.Status.SetDeployID(deployID)
			Expect(PreReleaseHook(bkapp)).To(Equal(fmt.Sprintf("pre-rel-foo-app-%s", deployID)))
		})
	})

	Context("Deployment", func() {
		DescribeTable("Different app and process names",
			func(appName string, process string, want string) {
				bkapp.Name = appName
				Expect(Deployment(bkapp, process)).To(Equal(want))
			},
			Entry("normal", "foo", "web", "foo--web"),
			Entry("_ in app", "foo_app", "web", "foo0us0app--web"),
			Entry("_ in process", "foo", "backend_worker", "foo--backend0us0worker"),
		)
	})
})
