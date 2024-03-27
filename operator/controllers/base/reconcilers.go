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

package base

import (
	"context"
	"time"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	ctrl "sigs.k8s.io/controller-runtime"
)

// Reconciler will move the current state of the cluster closer to the desired state.
type Reconciler interface {
	Reconcile(ctx context.Context, bkapp *paasv1alpha2.BkApp) Result
}

// Result ...
type Result struct {
	err      error
	duration time.Duration

	// IsFinished means that the result has been marked as finished
	IsFinished bool
}

// Duration get the duration value.
func (r Result) Duration() time.Duration {
	return r.duration
}

// Error get the error.
func (r Result) Error() error {
	return r.err
}

// ShouldAbort 返回是否需要中断当前调和循环
func (r Result) ShouldAbort() bool {
	return r.IsFinished || r.err != nil || r.duration.Seconds() != 0
}

// ToRepresentation 将 Result 对象转换成 kubebuilder 需要的返回值格式
func (r Result) ToRepresentation() (result ctrl.Result, err error) {
	if r.err != nil {
		return ctrl.Result{}, r.err
	}

	if r.IsFinished {
		return ctrl.Result{}, nil
	}

	duration := r.duration
	if duration.Seconds() == 0 {
		duration = paasv1alpha2.DefaultRequeueAfter
	}
	return ctrl.Result{RequeueAfter: duration}, nil
}

// WithError sets the error
func (r Result) WithError(err error) Result {
	r.err = err
	return r
}

// Requeue 设置下次触发调和循环的间隔
func (r Result) Requeue(duration time.Duration) Result {
	r.duration = duration
	return r
}

// End 结束调和循环, 如果没有出现异常
func (r Result) End() Result {
	r.IsFinished = true
	return r
}
