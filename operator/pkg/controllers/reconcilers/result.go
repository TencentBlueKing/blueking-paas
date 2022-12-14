/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
 * Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
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

package reconcilers

import (
	"time"

	ctrl "sigs.k8s.io/controller-runtime"

	"bk.tencent.com/paas-app-operator/api/v1alpha1"
)

// Result ...
type Result struct {
	err          error
	duration     time.Duration
	endReconcile bool
}

// ShouldAbort 返回是否需要中断当前调和循环
func (r Result) ShouldAbort() bool {
	return r.endReconcile || r.err != nil || r.duration.Seconds() != 0
}

// ToRepresentation 将 Result 对象转换成 kubebuilder 需要的返回值格式
func (r Result) ToRepresentation() (result ctrl.Result, err error) {
	if r.err != nil {
		return ctrl.Result{}, r.err
	}

	if r.endReconcile {
		return ctrl.Result{}, nil
	}

	duration := r.duration
	if duration.Seconds() == 0 {
		duration = v1alpha1.DefaultRequeueAfter
	}
	return ctrl.Result{RequeueAfter: duration}, nil
}

func (r Result) withError(err error) Result {
	r.err = err
	return r
}

// requeue 设置下次触发调和循环的间隔
func (r Result) requeue(duration time.Duration) Result {
	r.duration = duration
	return r
}

// End 结束调和循环, 如果没有出现异常
func (r Result) End() Result {
	r.endReconcile = true
	return r
}
