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
			ProcessCommands: map[string]map[string]string{"module1": {"proc1": "cmd1", "proc2": "cmd2"},
				"module2": {"proc1": "cmd1", "proc2": "cmd2"}},
			BuildGroups: []*plan.ModuleBuildGroup{
				{
					ModuleNames:        []string{"module1"},
					OutputImageTarName: "module1.tar",
				},
				{
					ModuleNames:        []string{"module2"},
					OutputImageTarName: "module2.tar",
				},
			}}
		Expect(writeArtifactJsonFile(&buildPlan, artifactJsonDir)).To(BeNil())

		fileContent, _ := os.ReadFile(filepath.Join(artifactJsonDir, "artifact.json"))

		Expect(gjson.GetBytes(fileContent, "module1.image_tar").String()).To(Equal("module1.tar"))
		Expect(gjson.GetBytes(fileContent, "module2.image_tar").String()).To(Equal("module2.tar"))

		Expect(gjson.GetBytes(fileContent, "module1.proc_entrypoints.proc1").Array()[0].String()).To(Equal("module1-proc1"))
		Expect(gjson.GetBytes(fileContent, "module1.proc_entrypoints.proc2").Array()[0].String()).To(Equal("module1-proc2"))
		Expect(gjson.GetBytes(fileContent, "module2.proc_entrypoints.proc1").Array()[0].String()).To(Equal("module2-proc1"))
		Expect(gjson.GetBytes(fileContent, "module2.proc_entrypoints.proc2").Array()[0].String()).To(Equal("module2-proc2"))
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
