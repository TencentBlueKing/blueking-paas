/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
 * Copyright (C) Tencent. All rights reserved.
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

package components_test

import (
	"os"
	"path/filepath"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

// The component definitions are duplicated across two deployment units: this
// repo ships them into the operator image, while apiserver reads its own copy to
// validate user input and render docs. A drift between the two shows up as
// "apiserver accepted it but the operator failed to render", which is painful to
// debug in a cluster, so it is caught here instead.
var _ = Describe("component definitions", func() {
	// Both paths are relative to this test file's package directory.
	const operatorComponentsDir = "../../../../../components"
	const apiserverComponentsDir = "../../../../../../apiserver/paasng/support-files/components"

	It("should stay in sync with the apiserver copy", func() {
		if _, err := os.Stat(apiserverComponentsDir); os.IsNotExist(err) {
			Skip("apiserver directory is not available in this checkout")
		}

		operatorFiles := collectComponentFiles(operatorComponentsDir)
		apiserverFiles := collectComponentFiles(apiserverComponentsDir)

		Expect(operatorFiles).NotTo(BeEmpty(), "no component found under operator/components")

		for relPath, operatorContent := range operatorFiles {
			apiserverContent, ok := apiserverFiles[relPath]
			Expect(ok).To(
				BeTrue(),
				"%s exists under operator/components but is missing from the apiserver copy", relPath,
			)
			Expect(string(operatorContent)).To(
				Equal(string(apiserverContent)),
				"%s differs between operator/components and the apiserver copy", relPath,
			)
		}
	})
})

// collectComponentFiles reads every component file under dir, keyed by its path
// relative to dir. The README is skipped: each copy documents its own context.
func collectComponentFiles(dir string) map[string][]byte {
	files := map[string][]byte{}
	err := filepath.Walk(dir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if info.IsDir() || info.Name() == "README.md" {
			return nil
		}
		relPath, err := filepath.Rel(dir, path)
		if err != nil {
			return err
		}
		content, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		files[relPath] = content
		return nil
	})
	Expect(err).NotTo(HaveOccurred())
	return files
}
