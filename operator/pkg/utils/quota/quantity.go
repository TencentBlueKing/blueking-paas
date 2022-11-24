/*
 * Tencent is pleased to support the open source community by making
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

package quota

import (
	"errors"
	"fmt"

	"gopkg.in/inf.v0"
	"k8s.io/apimachinery/pkg/api/resource"
)

// ResType 资源类型
type ResType string

const (
	// CPU cpu 资源
	CPU ResType = "cpu"
	// Memory 内存资源
	Memory ResType = "memory"
)

const (
	// cpu 最大资源配额（4核）
	maxCPU = "4"
	// 内存最大资源配额（4096Mi）
	maxMemory = "4Gi"
)

var (
	// ErrResQuotaRequired 必须配置资源配额
	ErrResQuotaRequired = errors.New("quota required")

	// ErrExceedLimit 资源配额超过上限
	ErrExceedLimit = errors.New("exceed limit")
)

var (
	// cpu 最大资源配额（4核）
	maxCPUQuantity = resource.MustParse(maxCPU)
	// 内存最大资源配额（4096Mi）
	maxMemoryQuantity = resource.MustParse(maxMemory)
)

const defaultScale = 3

// NewQuantity 创建 Quantity，包含校验检查
func NewQuantity(raw string, t ResType) (*resource.Quantity, error) {
	if raw == "" {
		return nil, ErrResQuotaRequired
	}
	q, err := resource.ParseQuantity(raw)
	if err != nil {
		return nil, err
	}

	// Limit 检查
	switch t {
	case CPU:
		if q.Cmp(maxCPUQuantity) > 0 {
			return nil, fmt.Errorf("%w: exceed cpu max limit %s", ErrExceedLimit, maxCPU)
		}
	case Memory:
		if q.Cmp(maxMemoryQuantity) > 0 {
			return nil, fmt.Errorf("%w: exceed memory max limit %s", ErrExceedLimit, maxMemory)
		}
	}
	return &q, nil
}

// Multi 对资源配额进行翻倍
func Multi(q *resource.Quantity, f int64) *resource.Quantity {
	n := inf.NewDec(0, 0).Mul(q.AsDec(), inf.NewDec(f, 0))
	return resource.NewDecimalQuantity(*n, q.Format)
}

// Div 对资源配额进行减半
func Div(q *resource.Quantity, d int64) *resource.Quantity {
	n := inf.NewDec(0, 0).QuoRound(q.AsDec(), inf.NewDec(d, 0), defaultScale, inf.RoundHalfEven)
	return resource.NewDecimalQuantity(*n, q.Format)
}
