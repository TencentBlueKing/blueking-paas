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

package vcs

import (
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

var _ = Describe("Test Types", func() {

	Context("Test Files", func() {
		It("AsTree", func() {
			files := Files{
				{Action: FileActionAdded, Path: "README.md"},
				{Action: FileActionAdded, Path: "webfe/static/example.css"},
				{Action: FileActionAdded, Path: "webfe/static/example.js"},
				{Action: FileActionDeleted, Path: "api/main.py"},
				{Action: FileActionDeleted, Path: "webfe/templates/example.html"},
				{Action: FileActionModified, Path: "backend/main.go"},
				{Action: FileActionModified, Path: "backend/types.go"},
				{Action: FileActionModified, Path: "docs/example.txt"},
			}

			excepted := &DirTree{
				Name: "",
				Dirs: []*DirTree{
					{
						Name: "api", Files: Files{
							{Action: FileActionDeleted, Path: "main.py"},
						},
					},
					{
						Name: "backend", Files: Files{
							{Action: FileActionModified, Path: "main.go"},
							{Action: FileActionModified, Path: "types.go"},
						},
					},
					{
						Name: "docs", Files: Files{
							{Action: FileActionModified, Path: "example.txt"},
						},
					},
					{
						Name: "webfe", Dirs: []*DirTree{
							{
								Name: "static", Files: Files{
									{Action: FileActionAdded, Path: "example.css"},
									{Action: FileActionAdded, Path: "example.js"},
								},
							},
							{
								Name: "templates", Files: Files{
									{Action: FileActionDeleted, Path: "example.html"},
								},
							},
						},
					},
				},
				Files: Files{
					{Action: FileActionAdded, Path: "README.md"},
				},
			}
			Expect(files.AsTree()).To(Equal(excepted))
		})

		It("AsTree with compress", func() {
			files := Files{
				{Action: FileActionAdded, Path: "webfe/static/example.css"},
				{Action: FileActionAdded, Path: "webfe/static/example.js"},
				{Action: FileActionDeleted, Path: "api/main.py"},
				{Action: FileActionDeleted, Path: "api/utils/stringx.py"},
				{Action: FileActionModified, Path: "backend/cmd/main.go"},
				{Action: FileActionModified, Path: "backend/pkg/types.go"},
				{Action: FileActionModified, Path: "docs/common/example.txt"},
				{Action: FileActionDeleted, Path: "mako/templates/mako/about_us.mako"},
				{Action: FileActionDeleted, Path: "example/templates/example/home/templates/home/home.html"},
				{Action: FileActionDeleted, Path: "example/templates/example/home/app.js"},
				{Action: FileActionDeleted, Path: "example/templates/example/home.html"},
				{Action: FileActionDeleted, Path: "example/apps.py"},
			}

			excepted := &DirTree{
				Name: "",
				Dirs: []*DirTree{
					{
						Name: "api",
						Dirs: []*DirTree{
							{
								Name: "utils", Files: Files{
									{Action: FileActionDeleted, Path: "stringx.py"},
								},
							},
						},
						Files: Files{
							{Action: FileActionDeleted, Path: "main.py"},
						},
					},
					{
						Name: "backend", Dirs: []*DirTree{
							{
								Name: "cmd", Files: Files{
									{Action: FileActionModified, Path: "main.go"},
								},
							},
							{
								Name: "pkg", Files: Files{
									{Action: FileActionModified, Path: "types.go"},
								},
							},
						},
					},
					{
						Name: "docs/common", Files: Files{
							{Action: FileActionModified, Path: "example.txt"},
						},
					},
					{
						Name: "example",
						Dirs: []*DirTree{
							{
								Name: "templates/example",
								Dirs: []*DirTree{
									{
										Name: "home",
										Dirs: []*DirTree{
											{
												Name: "templates/home",
												Files: Files{
													{Action: FileActionDeleted, Path: "home.html"},
												},
											},
										},
										Files: Files{
											{Action: FileActionDeleted, Path: "app.js"},
										},
									},
								},
								Files: Files{
									{Action: FileActionDeleted, Path: "home.html"},
								},
							},
						},
						Files: Files{
							{Action: FileActionDeleted, Path: "apps.py"},
						},
					},
					{
						Name: "mako/templates/mako",
						Files: Files{
							{Action: FileActionDeleted, Path: "about_us.mako"},
						},
					},
					{
						Name: "webfe/static", Files: Files{
							{Action: FileActionAdded, Path: "example.css"},
							{Action: FileActionAdded, Path: "example.js"},
						},
					},
				},
			}
			Expect(files.AsTree()).To(Equal(excepted))
		})
	})
})
