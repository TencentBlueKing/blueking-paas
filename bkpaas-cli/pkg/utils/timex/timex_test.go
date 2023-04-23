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

package timex_test

import (
	"strconv"
	"strings"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/TencentBlueKing/blueking-paas/client/pkg/utils/timex"
)

var _ = Describe("TestTimex", func() {
	DescribeTable(
		"TestCalcDuration",
		func(start, end, except string) {
			Expect(timex.CalcDuration(start, end)).To(Equal(except))
		},
		Entry("start > end", "2022-01-01 12:00:00", "2022-01-01 11:04:30", "-55m30s"),
		Entry("timeEqual", "2022-01-01 12:00:00", "2022-01-01 12:00:00", "< 1s"),
		Entry("millisecond", "2022-01-01 12:00:00.1234567", "2022-01-01 12:00:00.7654321", "641ms975µs"),
		Entry("second", "2022-01-01 12:00:00", "2022-01-01 12:00:01", "1s"),
		Entry("minSec", "2022-01-01 12:35:30", "2022-01-01 12:59:59", "24m29s"),
		Entry("hourSec", "2022-01-01 12:35:30", "2022-01-01 14:00:00", "1h24m"),
		Entry("dayHour1", "2022-01-01 12:35:30", "2022-01-03 14:00:00", "2d1h"),
		Entry("dayHour2", "2021-08-01 11:00:00", "2022-01-01 14:00:00", "153d3h"),
		Entry("dayHour3", "2021-04-01 11:00:00", "2022-01-01 14:00:00", "275d3h"),
		Entry("dayHour4", "2020-04-01 11:00:00", "2022-01-01 14:00:00", "640d3h"),
		Entry("k8sTimeFormat1", "2022-01-01T14:00:00Z", "2022-01-01T14:00:01Z", "1s"),
		Entry("k8sTimeFormat2", "2022-01-01T14:45:30Z", "2022-01-01T14:59:59Z", "14m29s"),
		Entry("k8sTimeFormat3", "2021-04-01T11:00:00Z", "2022-01-01T14:00:00Z", "275d3h"),
	)

	It("TestCalcAge", func() {
		// 存在时间会随运行时间而变化，这里直接比较大于 1000 天的时间
		age := timex.CalcAge("2019-01-01 11:00:00")
		dayCnt, _ := strconv.Atoi(strings.Split(age, "d")[0])
		Expect(dayCnt > 1000).To(BeTrue())
	})

	DescribeTable(
		"TestNormalizeDatetime",
		func(timeStr, except string, hasErr bool) {
			ret, err := timex.NormalizeDatetime(timeStr)
			Expect(ret).To(Equal(except))
			Expect(err != nil).To(Equal(hasErr))
		},
		Entry("rawFormat", "2023-01-01T12:00:00Z", "2023-01-01 12:00:00", false),
		Entry("k8sFormat", "2023-01-02 14:00:00", "2023-01-02 14:00:00", false),
		Entry("badFormat", "3/1/2023 12:00:00", "", true),
	)
})
