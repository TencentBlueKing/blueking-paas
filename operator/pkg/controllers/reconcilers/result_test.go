/*
 * Tencent is pleased to support the open source community by making BlueKing - PaaS System available.
 * Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 *  http://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under
 * the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 * either express or implied. See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * We undertake not to change the open source license (MIT license) applicable
 * to the current version of the project delivered to anyone in the future.
 */

package reconcilers

import (
	"errors"
	"time"

	"github.com/onsi/gomega/types"
	ctrl "sigs.k8s.io/controller-runtime"

	"bk.tencent.com/paas-app-operator/api/v1alpha1"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

var _ = Describe("Test Result", func() {
	DescribeTable("test ToRepresentation", func(
		ret Result,
		expectedResult ctrl.Result,
		errMatcher types.GomegaMatcher,
	) {
		result, err := ret.ToRepresentation()
		Expect(result).To(Equal(expectedResult))
		Expect(err).To(errMatcher)
	},
		Entry("normal case", Result{}, ctrl.Result{RequeueAfter: v1alpha1.DefaultRequeueAfter}, BeNil()),
		Entry("with error", Result{}.withError(errors.New("")), ctrl.Result{}, HaveOccurred()),
		Entry("requeue", Result{}.requeue(time.Second*60), ctrl.Result{RequeueAfter: time.Second * 60}, BeNil()),
		Entry("End", Result{}.End(), ctrl.Result{}, BeNil()),
		Entry("End with error", Result{}.withError(errors.New("")).End(), ctrl.Result{}, HaveOccurred()),
		Entry("End requeue", Result{}.requeue(time.Second*60).End(), ctrl.Result{}, BeNil()),
	)

	DescribeTable("test ShouldAbort", func(
		ret Result, shouldHangUp bool,
	) {
		Expect(ret.ShouldAbort()).To(Equal(shouldHangUp))
	},
		Entry("normal case", Result{}, false),
		Entry("with error", Result{}.withError(errors.New("")), true),
		Entry("requeue", Result{}.requeue(time.Second*60), true),
		Entry("End", Result{}.End(), true),
		Entry("End with error", Result{}.withError(errors.New("")).End(), true),
		Entry("End requeue", Result{}.requeue(time.Second*60).End(), true),
	)
})
