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

	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/utils"
)

var _ = Describe("GenBashCommandWithTokens", func() {
	// 正常情况
	DescribeTable("standard cases",
		func(command, args []string, expected string) {
			result := utils.GenBashCommandWithTokens(command, args)
			Expect(result).To(Equal(expected))
		},
		Entry("normal",
			[]string{"python"},
			[]string{"-m", "http.server"},
			`bash -c '"$(eval echo \"$0\")" "$(eval echo \"${1}\")" "$(eval echo \"${2}\")"'`+
				` 'python' '-m' 'http.server'`,
		),

		Entry("with env vars",
			[]string{"node"},
			[]string{"server.js", "${PORT:-8080}"},
			`bash -c '"$(eval echo \"$0\")" "$(eval echo \"${1}\")" "$(eval echo \"${2}\")"'`+
				` 'node' 'server.js' '${PORT:-8080}'`,
		),

		Entry("special chars",
			[]string{"echo"},
			[]string{"$PATH", "with space", "quote'd"},
			`bash -c '"$(eval echo \"$0\")" "$(eval echo \"${1}\")" "$(eval echo \"${2}\")" "$(eval echo \"${3}\")"'`+
				` 'echo' '$PATH' 'with space' 'quote'\''d'`,
		),

		Entry("empty args",
			[]string{"ls"},
			[]string{},
			`bash -c '"$(eval echo \"$0\")"' 'ls'`,
		),
	)

	Context("exception", func() {
		It("empty command", func() {
			result := utils.GenBashCommandWithTokens([]string{}, []string{"arg1"})
			Expect(result).To(Equal(`bash -c '"$(eval echo \"$0\")"' 'arg1'`))
		})

		It("empty command and args", func() {
			result := utils.GenBashCommandWithTokens([]string{}, []string{})
			Expect(result).To(Equal(`bash -c '"$(eval echo \"$0\")"'`))
		})
	})
})
