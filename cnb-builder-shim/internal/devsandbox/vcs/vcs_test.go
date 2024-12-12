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
	"os"
	"os/exec"
	"path"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

var _ = Describe("Test VersionController", func() {
	var tmpDir string

	var initFile = func(dir, filename, content string) error {
		if err := os.MkdirAll(dir, os.ModePerm); err != nil {
			return err
		}

		file, err := os.Create(path.Join(dir, filename))
		if err != nil {
			return err
		}
		defer file.Close()

		// 把文件名写入文件作为内容
		_, err = file.WriteString(content)
		return err
	}

	var editFile = func(dir, filename, content string) error {
		file, err := os.OpenFile(path.Join(dir, filename), os.O_WRONLY|os.O_TRUNC, 0644)
		if err != nil {
			return err
		}
		defer file.Close()

		// 追加内容到文件
		_, err = file.WriteString(content)
		return err
	}

	var runGitCommand = func(dir string, args ...string) error {
		cmd := exec.Command("git", args...)
		cmd.Dir = dir
		return cmd.Run()
	}

	// 初始化临时目录 & 文件
	BeforeEach(func() {
		tmpDir, _ = os.MkdirTemp("", "vcs")
		for _, filename := range []string{"example.txt", "example.py", "example.go"} {
			Expect(initFile(tmpDir, filename, path.Ext(filename))).To(BeNil())
		}
	})
	// 清理临时目录
	AfterEach(func() {
		Expect(os.RemoveAll(tmpDir)).To(BeNil())
	})

	Context("Test VersionController", func() {
		It("with .git", func() {
			Expect(runGitCommand(tmpDir, "init")).To(BeNil())
			Expect(runGitCommand(tmpDir, "add", ".")).To(BeNil())
			Expect(runGitCommand(tmpDir, "config", "user.name", "bkpaas")).To(BeNil())
			Expect(runGitCommand(tmpDir, "config", "user.email", "bkpaas@example.com")).To(BeNil())
			Expect(runGitCommand(tmpDir, "commit", "-m", "init")).To(BeNil())

			verCtrl := New(WithContent())
			Expect(verCtrl.Prepare(tmpDir)).To(BeNil())

			files, err := verCtrl.Diff()
			Expect(err).To(BeNil())
			Expect(files).To(HaveLen(0))

			_ = initFile(tmpDir, "example.html", ".html")
			_ = initFile(tmpDir, "example.js", ".js")

			files, err = verCtrl.Diff()
			Expect(err).To(BeNil())
			Expect(files).To(Equal(Files{
				{Action: FileActionAdded, Path: "example.html", Content: ".html"},
				{Action: FileActionAdded, Path: "example.js", Content: ".js"},
			}))

			_ = os.Remove(path.Join(tmpDir, "example.html"))
			_ = os.Remove(path.Join(tmpDir, "example.py"))
			files, err = verCtrl.Diff()
			Expect(err).To(BeNil())
			Expect(files).To(Equal(Files{
				{Action: FileActionAdded, Path: "example.js", Content: ".js"},
				{Action: FileActionDeleted, Path: "example.py", Content: ""},
			}))

			_ = editFile(tmpDir, "example.go", "gogo")
			files, err = verCtrl.Diff()
			Expect(err).To(BeNil())
			Expect(files).To(Equal(Files{
				{Action: FileActionModified, Path: "example.go", Content: "gogo"},
				{Action: FileActionAdded, Path: "example.js", Content: ".js"},
				{Action: FileActionDeleted, Path: "example.py", Content: ""},
			}))
		})

		It("without .git", func() {
			verCtrl := New(WithContent())
			Expect(verCtrl.Prepare(tmpDir)).To(BeNil())

			files, err := verCtrl.Diff()
			Expect(err).To(BeNil())
			Expect(files).To(HaveLen(0))

			_ = initFile(path.Join(tmpDir, "webfe/templates"), "example.html", ".html")
			_ = initFile(path.Join(tmpDir, "webfe/static"), "example.js", ".js")
			_ = initFile(path.Join(tmpDir, "webfe/static"), "example.css", ".css")
			_ = os.Remove(path.Join(tmpDir, "webfe/templates/example.html"))
			_ = os.Remove(path.Join(tmpDir, "example.py"))
			_ = editFile(tmpDir, "example.go", "gogo")
			_ = editFile(path.Join(tmpDir, "webfe/static"), "example.js", "js-js")
			_ = editFile(tmpDir, "example.txt", "txt no.1")

			files, err = verCtrl.Diff()
			Expect(err).To(BeNil())
			Expect(files).To(HaveLen(5))
			Expect(files).To(Equal(Files{
				{Action: FileActionModified, Path: "example.go", Content: "gogo"},
				{Action: FileActionDeleted, Path: "example.py", Content: ""},
				{Action: FileActionModified, Path: "example.txt", Content: "txt no.1"},
				{Action: FileActionAdded, Path: "webfe/static/example.css", Content: ".css"},
				{Action: FileActionAdded, Path: "webfe/static/example.js", Content: "js-js"},
			}))
		})

		It("with ignore", func() {
			verCtrl := New(WithContent())
			Expect(verCtrl.Prepare(tmpDir)).To(BeNil())

			_ = initFile(path.Join(tmpDir, "webfe/templates"), "example.html", ".html")
			_ = initFile(path.Join(tmpDir, "v3logs"), "celery.log", "celery is running...")
			_ = initFile(path.Join(tmpDir, "v3logs"), "gunicorn.log", "gunicorn is running...")
			_ = editFile(tmpDir, "example.txt", "txt no.1")
			_ = os.Remove(path.Join(tmpDir, "example.go"))

			files, err := verCtrl.Diff()
			Expect(err).To(BeNil())
			Expect(files).To(Equal(Files{
				{Action: FileActionDeleted, Path: "example.go", Content: ""},
				{Action: FileActionModified, Path: "example.txt", Content: "txt no.1"},
				{Action: FileActionAdded, Path: "webfe/templates/example.html", Content: ".html"},
			}))
		})

		It("without content", func() {
			verCtrl := New()
			Expect(verCtrl.Prepare(tmpDir)).To(BeNil())

			_ = initFile(path.Join(tmpDir, "webfe/static"), "example.css", "css")
			_ = initFile(path.Join(tmpDir, "v3logs"), "celery.log", "celery is running...")
			_ = editFile(tmpDir, "example.py", "python")
			_ = os.Remove(path.Join(tmpDir, "example.go"))

			files, err := verCtrl.Diff()
			Expect(err).To(BeNil())
			Expect(files).To(Equal(Files{
				{Action: FileActionDeleted, Path: "example.go", Content: ""},
				{Action: FileActionModified, Path: "example.py", Content: ""},
				{Action: FileActionAdded, Path: "webfe/static/example.css", Content: ""},
			}))
		})

		It("with special chars", func() {
			verCtrl := New(WithContent())
			Expect(verCtrl.Prepare(tmpDir)).To(BeNil())

			_ = initFile(tmpDir, "example space.css", "css 代码")
			_ = initFile(tmpDir, "example——中文.js", "js 代码")
			_ = initFile(tmpDir, "example.tab.html", "html 代码")

			files, err := verCtrl.Diff()
			Expect(err).To(BeNil())
			Expect(files).To(Equal(Files{
				{Action: FileActionAdded, Path: "example space.css", Content: "css 代码"},
				{Action: FileActionAdded, Path: "example.tab.html", Content: "html 代码"},
				{Action: FileActionAdded, Path: "example——中文.js", Content: "js 代码"},
			}))
		})
	})
})
