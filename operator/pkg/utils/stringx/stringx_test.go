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

package stringx_test

import (
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"bk.tencent.com/paas-app-operator/pkg/utils/stringx"
)

var _ = Describe("Test stringx tools", func() {
	DescribeTable("test RandLetters", func(length int) {
		Expect(len(stringx.RandLetters(length))).To(Equal(length))
	},
		Entry("zero", 0),
		Entry("eight", 8),
		Entry("hundred", 128),
		Entry("thousand", 1024),
	)

	It("test ToStrArray with alias", func() {
		type MyString string
		Expect(stringx.ToStrArray([]MyString{"2C", "2TB"})).To(Equal([]string{"2C", "2TB"}))
	})

	It("test ToStrArray without alias", func() {
		Expect(stringx.ToStrArray([]string{"2C", "2TB"})).To(Equal([]string{"2C", "2TB"}))
	})
})
