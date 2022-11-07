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

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

var _ = Describe("TestResQuota", func() {
	DescribeTable(
		"test ResQuota.String()",
		func(t ResType, raw, s string) {
			q, err := New(t, raw)
			Expect(err).ShouldNot(HaveOccurred())
			Expect(q.String()).To(Equal(s))
		},
		Entry("cpu unit m", CPU, "200m", "200m"),
		Entry("cpu no unit", CPU, "4", "4000m"),
		Entry("mem unit Mi", Memory, "300Mi", "300Mi"),
		Entry("mem unit Gi", Memory, "2Gi", "2048Mi"),
	)

	DescribeTable(
		"test ResQuota.Half()",
		func(t ResType, raw, s string) {
			q, err := New(t, raw)
			Expect(err).ShouldNot(HaveOccurred())
			Expect(q.Half().String()).To(Equal(s))
		},
		Entry("cpu unit m", CPU, "200m", "100m"),
		Entry("cpu no unit", CPU, "4", "2000m"),
		Entry("mem unit Mi", Memory, "300Mi", "150Mi"),
		Entry("mem unit Gi", Memory, "2Gi", "1024Mi"),
		Entry("after convert unit", CPU, "1", "500m"),
		Entry("odd val half", CPU, "25m", "12m"),
		Entry("min val half", CPU, "1m", "1m"),
	)

	DescribeTable(
		"test ResQuota.RealHalf() error case",
		func(t ResType, raw string) {
			q, _ := New(t, raw)
			_, err := q.RealHalf()
			Expect(errors.Is(err, ErrPrecisionLoss)).To(BeTrue())
		},
		Entry("cpu unit m", CPU, "75m"),
		Entry("mem unit Mi", Memory, "155Mi"),
	)

	DescribeTable(
		"test ResQuota.Quarter()",
		func(t ResType, raw, s string) {
			q, err := New(t, raw)
			Expect(err).ShouldNot(HaveOccurred())
			Expect(q.Quarter().String()).To(Equal(s))
		},
		Entry("cpu unit m", CPU, "200m", "50m"),
		Entry("cpu no unit", CPU, "4", "1000m"),
		Entry("mem unit Mi", Memory, "300Mi", "75Mi"),
		Entry("mem unit Gi", Memory, "2Gi", "512Mi"),
		Entry("after convert unit", CPU, "1", "250m"),
		Entry("odd val quarter", CPU, "25m", "6m"),
		Entry("min val quarter", CPU, "4m", "1m"),
		Entry("min + odd val quarter", CPU, "3m", "1m"),
	)

	DescribeTable(
		"test ResQuota.RealHalf() normal case",
		func(t ResType, raw, s string) {
			q, _ := New(t, raw)
			rh, _ := q.RealHalf()
			Expect(rh.String()).To(Equal(s))
		},
		Entry("cpu unit m", CPU, "200m", "100m"),
		Entry("cpu no unit", CPU, "4", "2000m"),
		Entry("mem unit Mi", Memory, "300Mi", "150Mi"),
		Entry("mem unit Gi", Memory, "2Gi", "1024Mi"),
		Entry("after convert unit", CPU, "1", "500m"),
	)

	DescribeTable(
		"test ResQuota.Double()",
		func(t ResType, raw, s string) {
			q, err := New(t, raw)
			Expect(err).ShouldNot(HaveOccurred())
			Expect(q.Double().String()).To(Equal(s))
		},
		Entry("cpu unit m", CPU, "200m", "400m"),
		Entry("cpu no unit", CPU, "2", "4000m"),
		Entry("mem unit Mi", Memory, "300Mi", "600Mi"),
		Entry("mem unit Gi", Memory, "2Gi", "4096Mi"),
	)

	DescribeTable(
		"test ResQuota.RealDouble() error case",
		func(t ResType, raw string) {
			q, _ := New(t, raw)
			_, err := q.RealDouble()
			Expect(errors.Is(err, ErrExceedLimit)).To(BeTrue())
		},
		Entry("cpu exceed limit 1", CPU, "2500m"),
		Entry("cpu exceed limit 2", CPU, "3"),
		Entry("mem exceed limit 1", Memory, "2500Mi"),
		Entry("mem exceed limit 2", Memory, "3Gi"),
	)

	DescribeTable(
		"test ResQuota.RealDouble() normal case",
		func(t ResType, raw, s string) {
			q, _ := New(t, raw)
			rd, _ := q.RealDouble()
			Expect(rd.String()).To(Equal(s))
		},
		Entry("cpu unit m", CPU, "200m", "400m"),
		Entry("cpu no unit", CPU, "1", "2000m"),
		Entry("mem unit Mi", Memory, "300Mi", "600Mi"),
		Entry("mem unit Gi", Memory, "1Gi", "2048Mi"),
	)

	It("unsupported case", func() {
		_, err := New(CPU, "2C")
		Expect(errors.Is(err, ErrUnsupported)).To(BeTrue())

		_, err = New(Memory, "2Ti")
		Expect(errors.Is(err, ErrUnsupported)).To(BeTrue())

		_, err = New(CPU, "2.5")
		Expect(errors.Is(err, ErrUnsupported)).To(BeTrue())
		Expect(err.Error()).To(Equal("unsupported: decimals are not supported"))
	})

	It("exceed limit case", func() {
		_, err := New(CPU, "6")
		Expect(errors.Is(err, ErrExceedLimit)).To(BeTrue())
		Expect(err.Error()).To(Equal("exceed limit: exceed cpu max limit 4000m"))

		_, err = New(Memory, "5000Mi")
		Expect(errors.Is(err, ErrExceedLimit)).To(BeTrue())
		Expect(err.Error()).To(Equal("exceed limit: exceed memory max limit 4096Mi"))
	})

	It("resource quota required", func() {
		_, err := New(CPU, "")
		Expect(errors.Is(err, ErrResQuotaRequired)).To(BeTrue())

		_, err = New(Memory, "")
		Expect(errors.Is(err, ErrResQuotaRequired)).To(BeTrue())
	})
})
