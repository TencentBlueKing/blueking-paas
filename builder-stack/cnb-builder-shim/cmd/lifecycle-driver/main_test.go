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

package main

import (
	"context"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

var _ = Describe("Test lifecycle driver", func() {
	Describe("Test get Steps", func() {
		Context("Test get getBuilderSteps", func() {
			var oldCacheImage string

			BeforeEach(func() {
				oldCacheImage = *cacheImage
			})
			AfterEach(func() {
				*cacheImage = oldCacheImage
			})

			It("Test get getBuilderSteps without cache image", func() {
				*cacheImage = ""
				expectedStepOrder := []string{"Analyze", "Detect", "Build", "Export"}

				ctx := context.Background()
				steps := getBuilderSteps(ctx)
				stepOrder := []string{}
				for _, step := range steps {
					stepOrder = append(stepOrder, step.Name)
				}

				Expect(stepOrder).To(Equal(expectedStepOrder))
			})
			It("Test get getBuilderSteps with cache image", func() {
				*cacheImage = "testcache:latest"
				expectedStepOrder := []string{"Analyze", "Detect", "Restore", "Build", "Export"}

				ctx := context.Background()
				steps := getBuilderSteps(ctx)
				stepOrder := []string{}
				for _, step := range steps {
					stepOrder = append(stepOrder, step.Name)
				}

				Expect(stepOrder).To(Equal(expectedStepOrder))
			})
		})
		Context("Test get getDevSteps", func() {
			It("Test get getDevSteps", func() {
				expectedStepOrder := []string{"Detect", "Build"}

				ctx := context.Background()
				steps := getDevSteps(ctx)
				stepOrder := []string{}
				for _, step := range steps {
					stepOrder = append(stepOrder, step.Name)
				}

				Expect(stepOrder).To(Equal(expectedStepOrder))
			})
		})
	})
})
