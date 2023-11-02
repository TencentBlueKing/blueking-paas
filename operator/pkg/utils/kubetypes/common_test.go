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

package kubetypes

import (
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	appsv1 "k8s.io/api/apps/v1"
)

var _ = Describe("Test get/set JSON annotations", func() {
	It("Set invalid JSON value", func() {
		d := &appsv1.Deployment{}
		// Chan is not JSON serializable
		Expect(SetJsonAnnotation(d, "test", make(chan int))).To(HaveOccurred())
	})

	It("Get not found", func() {
		d := &appsv1.Deployment{}
		val, err := GetJsonAnnotation[map[string]string](d, "test")
		Expect(err).To(HaveOccurred())
		Expect(val).To(BeNil())
	})

	It("Integrated test, normal case", func() {
		d := &appsv1.Deployment{}
		err := SetJsonAnnotation(d, "test", map[string]string{"foo": "bar"})
		Expect(err).NotTo(HaveOccurred())

		// Get the value set above
		val, err := GetJsonAnnotation[map[string]string](d, "test")
		Expect(err).NotTo(HaveOccurred())
		Expect(val).To(Equal(map[string]string{"foo": "bar"}))
	})
})

var _ = DescribeTable("Test ReplaceCommandEnvVariables",
	func(input, expected []string) {
		Expect(ReplaceCommandEnvVariables(input)).To(Equal(expected))
	},
	Entry("no var", []string{"/start.sh"}, []string{"/start.sh"}),
	Entry("var format-1", []string{"start", "-p", "$PORT"}, []string{"start", "-p", "$(PORT)"}),
	Entry("var format-2", []string{"start", "-l", "http://${HOST}/"}, []string{"start", "-l", "http://$(HOST)/"}),
	Entry("near variables", []string{"$FOO$BAR"}, []string{"$(FOO)$(BAR)"}),
	Entry("escaped dollar symbol", []string{"echo", "dollar: \\$not_var"}, []string{"echo", "dollar: \\$not_var"}),
)
