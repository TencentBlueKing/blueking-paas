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

package quota

import (
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	"github.com/pkg/errors"
	"k8s.io/apimachinery/pkg/api/resource"
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
			q, _ := NewQuantity(raw, t)
			Expect(Div(q, 2).Cmp(resource.MustParse(s))).To(Equal(0))
		},
		Entry("cpu unit m", CPU, "200m", "100m"),
		Entry("cpu no unit", CPU, "4", "2000m"),
		Entry("mem unit Mi", Memory, "300Mi", "150Mi"),
		Entry("mem unit Gi", Memory, "2Gi", "1024Mi"),
		Entry("after convert unit", CPU, "1", "500m"),
		// test case: If the maximum value is exceeded, the maximum value will be returned
		Entry("Memory max limit(bigger than 65536Mi)", Memory, "140000Mi", "32768Mi"),
		Entry("CPU max limit(bigger than 48000m)", CPU, "100000m", "24000m"),
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
		q, err := NewQuantity("2C", CPU)
		Expect(err.Error()).To(ContainSubstring("quantities must match the regular expression"))
		Expect(q).NotTo(BeNil())

		q, err = NewQuantity("2TB", Memory)
		Expect(err.Error()).To(ContainSubstring("quantities must match the regular expression"))
		Expect(q).NotTo(BeNil())
	})

	It("exceed limit case", func() {
		_, err := NewQuantity("64", CPU)
		Expect(errors.Is(err, ErrExceedLimit)).To(BeTrue())
		Expect(err.Error()).To(Equal("exceed cpu max limit 48: exceed limit"))

		_, err = NewQuantity("70000Mi", Memory)
		Expect(errors.Is(err, ErrExceedLimit)).To(BeTrue())
		Expect(err.Error()).To(Equal("exceed memory max limit 64Gi: exceed limit"))
	})

	Describe("ParseResourceSpec", func() {
		It("should parse valid CPU and Memory", func() {
			cpu, mem, err := ParseResourceSpec("200m", "512Mi")
			Expect(err).NotTo(HaveOccurred())
			Expect(cpu.Cmp(resource.MustParse("200m"))).To(Equal(0))
			Expect(mem.Cmp(resource.MustParse("512Mi"))).To(Equal(0))
		})

		It("should parse valid CPU and Memory with different units", func() {
			cpu, mem, err := ParseResourceSpec("2", "2Gi")
			Expect(err).NotTo(HaveOccurred())
			Expect(cpu.Cmp(resource.MustParse("2"))).To(Equal(0))
			Expect(mem.Cmp(resource.MustParse("2Gi"))).To(Equal(0))
		})

		It("should fail with invalid CPU", func() {
			_, _, err := ParseResourceSpec("invalid-cpu", "512Mi")
			Expect(err).To(HaveOccurred())
			Expect(err.Error()).To(ContainSubstring("invalid cpu value"))
		})

		It("should fail with invalid Memory", func() {
			_, _, err := ParseResourceSpec("200m", "invalid-memory")
			Expect(err).To(HaveOccurred())
			Expect(err.Error()).To(ContainSubstring("invalid memory value"))
		})

		It("should fail with empty CPU", func() {
			_, _, err := ParseResourceSpec("", "512Mi")
			Expect(err).To(HaveOccurred())
			Expect(err.Error()).To(ContainSubstring("invalid cpu value"))
		})

		It("should fail with empty Memory", func() {
			_, _, err := ParseResourceSpec("200m", "")
			Expect(err).To(HaveOccurred())
			Expect(err.Error()).To(ContainSubstring("invalid memory value"))
		})

		It("should enforce CPU limit", func() {
			_, _, err := ParseResourceSpec("64", "512Mi")
			Expect(err).To(HaveOccurred())
			Expect(err.Error()).To(ContainSubstring("exceed cpu max limit"))
		})

		It("should enforce Memory limit", func() {
			_, _, err := ParseResourceSpec("200m", "128Gi")
			Expect(err).To(HaveOccurred())
			Expect(err.Error()).To(ContainSubstring("exceed memory max limit"))
		})
	})
})
