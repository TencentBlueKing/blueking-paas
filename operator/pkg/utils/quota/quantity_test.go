/*
 * Tencent is pleased to support the open source community by making BlueKing - PaaS System available.
 * Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 * 	http://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under
 * the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 * either express or implied. See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * We undertake not to change the open source license (MIT license) applicable
 * to the current version of the project delivered to anyone in the future.
 */

package quota

import (
	"errors"

	"k8s.io/apimachinery/pkg/api/resource"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

var _ = Describe("TestQuota", func() {
	DescribeTable(
		"test Multi() 2",
		func(t ResType, raw, s string) {
			q, err := NewQuantity(raw, t)
			Expect(err).ShouldNot(HaveOccurred())
			Expect(Multi(q, 2).Cmp(resource.MustParse(s))).To(Equal(0))
		},
		Entry("cpu unit m", CPU, "200m", "400m"),
		Entry("cpu no unit", CPU, "4", "8"),
		Entry("mem unit Mi", Memory, "300Mi", "600Mi"),
		Entry("mem unit Gi", Memory, "2Gi", "4096Mi"),
	)

	DescribeTable(
		"test Multi() 3",
		func(t ResType, raw, s string) {
			q, err := NewQuantity(raw, t)
			Expect(err).ShouldNot(HaveOccurred())
			Expect(Multi(q, 3).Cmp(resource.MustParse(s))).To(Equal(0))
		},
		Entry("cpu unit m", CPU, "200m", "600m"),
		Entry("cpu no unit", CPU, "4", "12"),
		Entry("mem unit Mi", Memory, "300Mi", "900Mi"),
		Entry("mem unit Gi", Memory, "2Gi", "6Gi"),
	)

	DescribeTable(
		"test Div() 2",
		func(t ResType, raw, s string) {
			q, err := NewQuantity(raw, t)
			Expect(err).ShouldNot(HaveOccurred())
			Expect(Div(q, 2).Cmp(resource.MustParse(s))).To(Equal(0))
		},
		Entry("cpu unit m", CPU, "200m", "100m"),
		Entry("cpu no unit", CPU, "4", "2000m"),
		Entry("mem unit Mi", Memory, "300Mi", "150Mi"),
		Entry("mem unit Gi", Memory, "2Gi", "1024Mi"),
		Entry("after convert unit", CPU, "1", "500m"),
	)

	DescribeTable(
		"test Div() 3",
		func(t ResType, raw, s string) {
			q, err := NewQuantity(raw, t)
			Expect(err).ShouldNot(HaveOccurred())
			Expect(Div(q, 3).Cmp(resource.MustParse(s))).To(Equal(0))
		},
		Entry("cpu unit m", CPU, "200m", "67m"),
		Entry("cpu no unit", CPU, "4", "1333m"),
		Entry("mem unit Mi", Memory, "300Mi", "100Mi"),
		Entry("mem unit Gi", Memory, "3Gi", "1024Mi"),
		Entry("after convert unit", CPU, "1", "333m"),
	)

	It("parse error case", func() {
		_, err := NewQuantity("2C", CPU)
		Expect(err.Error()).To(ContainSubstring("quantities must match the regular expression"))

		_, err = NewQuantity("2TB", Memory)
		Expect(err.Error()).To(ContainSubstring("quantities must match the regular expression"))
	})

	It("exceed limit case", func() {
		_, err := NewQuantity("6", CPU)
		Expect(errors.Is(err, ErrExceedLimit)).To(BeTrue())
		Expect(err.Error()).To(Equal("exceed limit: exceed cpu max limit 4"))

		_, err = NewQuantity("5000Mi", Memory)
		Expect(errors.Is(err, ErrExceedLimit)).To(BeTrue())
		Expect(err.Error()).To(Equal("exceed limit: exceed memory max limit 4Gi"))
	})
})
