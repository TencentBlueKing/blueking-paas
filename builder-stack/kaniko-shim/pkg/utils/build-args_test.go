/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
 * Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 *     http://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under
 * the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 * either express or implied. See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * We undertake not to change the open source license (MIT license) applicable
 * to the current version of the project delivered to anyone in the future.
 */
package utils_test

import (
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/TencentBlueking/bkpaas/kaniko-shim/pkg/utils"
)

var _ = Describe("ParseBuildArgs", func() {
	DescribeTable("Test ParseBuildArgs", func(buildArgs string, expected []string) {
		Expect(utils.ParseBuildArgs(buildArgs)).To(Equal(expected))
	},
		Entry("empty", "", nil),
		Entry("single", "YT1h", []string{"a=a"}),
		Entry("complex case",
			"RU5WMT1MT05HTE9OR0xPTkdMT05HTE9OR0xPTkdMT05HTE9OR0xPTkdMT05HTE9OR0xPTkdMT05HTE9OR0xPTkdMT05HTE9OR0xPTkdMT05HTE9OR0xPTkc=,RU5WMj1BUkcgV0lUSCBTUEFDRQ==",
			[]string{
				"ENV1=LONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONGLONG", "ENV2=ARG WITH SPACE",
			}),
	)
})
