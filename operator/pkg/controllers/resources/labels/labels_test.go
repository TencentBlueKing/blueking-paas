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

package labels

import (
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
)

var _ = Describe("Get resource labels", func() {
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

	Context("Deployment", func() {
		DescribeTable(
			"Different app and process names",
			func(appName string, process string, want map[string]string) {
				bkapp.Name = appName
				Expect(Deployment(bkapp, process)).To(Equal(want))
			},
			Entry(
				"normal",
				"foo",
				"web",
				map[string]string{paasv1alpha2.BkAppNameKey: "foo", paasv1alpha2.ProcessNameKey: "web"},
			),
			Entry(
				"_ in app",
				"foo_app",
				"web",
				map[string]string{paasv1alpha2.BkAppNameKey: "foo_app", paasv1alpha2.ProcessNameKey: "web"},
			),
			Entry(
				"_ in process",
				"foo",
				"backend_worker",
				map[string]string{paasv1alpha2.BkAppNameKey: "foo", paasv1alpha2.ProcessNameKey: "backend_worker"},
			),
		)
	})
})
