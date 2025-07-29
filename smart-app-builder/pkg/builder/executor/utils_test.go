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

package executor

import (
	"os"
	"path/filepath"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	"github.com/tidwall/gjson"

	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/plan"
)

var _ = Describe("writeArtifactJsonFile", func() {
	var artifactJsonDir string

	BeforeEach(func() {
		artifactJsonDir, _ = os.MkdirTemp("", "tmp")
	})
	AfterEach(func() {
		Expect(os.RemoveAll(artifactJsonDir)).To(BeNil())
	})

	It("Each module uses its own independent image tar", func() {
		buildPlan := plan.BuildPlan{
			ProcessCommands: map[string]map[string]string{
				"module1": {"proc1": "cmd1", "proc2": "cmd2"},
				"module2": {"proc1": "cmd1", "proc2": "cmd2"},
			},
			BuildGroups: []*plan.ModuleBuildGroup{
				{
					ModuleNames:        []string{"module1"},
					OutputImageTarName: "module1.tar",
				},
				{
					ModuleNames:        []string{"module2"},
					OutputImageTarName: "module2.tar",
				},
			},
		}
		Expect(writeArtifactJsonFile(&buildPlan, artifactJsonDir)).To(BeNil())

		fileContent, _ := os.ReadFile(filepath.Join(artifactJsonDir, "artifact.json"))

		Expect(gjson.GetBytes(fileContent, "module1.image_tar").String()).To(Equal("module1.tar"))
		Expect(gjson.GetBytes(fileContent, "module2.image_tar").String()).To(Equal("module2.tar"))

		Expect(
			gjson.GetBytes(fileContent, "module1.proc_entrypoints.proc1").Array()[0].String(),
		).To(Equal("module1-proc1"))
		Expect(
			gjson.GetBytes(fileContent, "module1.proc_entrypoints.proc2").Array()[0].String(),
		).To(Equal("module1-proc2"))
		Expect(
			gjson.GetBytes(fileContent, "module2.proc_entrypoints.proc1").Array()[0].String(),
		).To(Equal("module2-proc1"))
		Expect(
			gjson.GetBytes(fileContent, "module2.proc_entrypoints.proc2").Array()[0].String(),
		).To(Equal("module2-proc2"))
	})

	It("Some module uses the same image tar", func() {
		buildPlan := plan.BuildPlan{BuildGroups: []*plan.ModuleBuildGroup{
			{
				ModuleNames:        []string{"module1", "module2"},
				OutputImageTarName: "module1.tar",
			},
			{
				ModuleNames:        []string{"module3"},
				OutputImageTarName: "module3.tar",
			},
		}}
		Expect(writeArtifactJsonFile(&buildPlan, artifactJsonDir)).To(BeNil())

		fileContent, _ := os.ReadFile(filepath.Join(artifactJsonDir, "artifact.json"))

		Expect(gjson.GetBytes(fileContent, "module1.image_tar").String()).To(Equal("module1.tar"))
		Expect(gjson.GetBytes(fileContent, "module2.image_tar").String()).To(Equal("module1.tar"))
		Expect(gjson.GetBytes(fileContent, "module3.image_tar").String()).To(Equal("module3.tar"))
	})
})
