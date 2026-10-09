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

var _ = Describe("ParseRegistryMap", func() {
	DescribeTable("valid", func(registryMap string, expected []string) {
		Expect(utils.ParseRegistryMap(registryMap)).To(Equal(expected))
	},
		Entry("empty", "", nil),
		Entry("single",
			"mirrors.example.com=proxy.example.com/mirrors-example-com",
			[]string{"mirrors.example.com=proxy.example.com/mirrors-example-com"},
		),
		Entry("with port",
			"registry.local:5000=proxy.example.com:8443/registry-local-5000",
			[]string{"registry.local:5000=proxy.example.com:8443/registry-local-5000"},
		),
		Entry("multiple",
			"a.com=proxy.example.com/a-com,b.com=proxy.example.com/b-com",
			[]string{"a.com=proxy.example.com/a-com", "b.com=proxy.example.com/b-com"},
		),
	)

	DescribeTable("invalid", func(registryMap string) {
		_, err := utils.ParseRegistryMap(registryMap)
		Expect(err).To(HaveOccurred())
	},
		Entry("no separator", "mirrors.example.com"),
		Entry("empty registry", "=proxy.example.com/a"),
		Entry("empty prefix", "mirrors.example.com="),
		Entry("multiple separators", "a.com=b.com=c.com"),
		Entry("empty item", "a.com=proxy.example.com/a-com,"),
		Entry("semicolon", "a.com=proxy.example.com/a-com;b.com=proxy.example.com/b-com"),
		Entry("whitespace", "a.com=proxy.example.com/a-com, b.com=proxy.example.com/b-com"),
		Entry("scheme", "a.com=https://proxy.example.com/a-com"),
	)
})
