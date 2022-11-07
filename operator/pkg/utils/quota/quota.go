/*
 * Tencent is pleased to support the open source community by making BlueKing - PaaS System available.
 * Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 * 	http://opensource.org/licenses/MIT
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
	"strconv"
	"unicode"

	"github.com/samber/lo"
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
	// NoUnit 无单位（CPU）
	NoUnit = ""
	// UnitM 单位 m（CPU）
	UnitM = "m"
	// UnitMi 单位 Mi（内存）
	UnitMi = "Mi"
	// UnitGi 单位 Gi（内存）
	UnitGi = "Gi"
)

const (
	// cpu 最大资源配额（4核）
	maxCPU = 4000
	// 内存最大资源配额（4096Mi）
	maxMemory = 4096
)

var (
	// cpu 资源配额支持的单位
	cpuSupportedUnits = []string{NoUnit, UnitM}

	// 内存资源配额支持的单位
	memorySupportedUnits = []string{UnitMi, UnitGi}
)

var (
	// ErrPrecisionLoss 精度丢失
	ErrPrecisionLoss = errors.New("loss precision")

	// ErrUnsupported 不受支持的类型/单位
	ErrUnsupported = errors.New("unsupported")

	// ErrExceedLimit 资源配额超过上限
	ErrExceedLimit = errors.New("exceed limit")

	// ErrResQuotaRequired 必须配置资源配额
	ErrResQuotaRequired = errors.New("quota required")
)

// ResQuota 资源配额
type ResQuota struct {
	_type ResType
	raw   string
	value int
	unit  string
}

// New ...
func New(t ResType, raw string) (*ResQuota, error) {
	if raw == "" {
		return nil, ErrResQuotaRequired
	}
	quota := ResQuota{_type: t, raw: raw}
	if err := quota.format(); err != nil {
		return nil, err
	}
	if err := quota.validate(); err != nil {
		return nil, err
	}
	return &quota, nil
}

// String 获取资源配置原始字符串
func (q *ResQuota) String() string {
	return strconv.Itoa(q.value) + q.unit
}

// Half 获取减半的资源配额（向下取整，最小值为 1）
func (q *ResQuota) Half() *ResQuota {
	val := lo.Max([]int{q.value / 2, 1})
	quota, _ := New(q._type, strconv.Itoa(val)+q.unit)
	return quota
}

// RealHalf 获取准确减半的资源配额，当减半会丢失精度时，抛出 error
func (q *ResQuota) RealHalf() (*ResQuota, error) {
	if q.value&1 != 0 {
		return nil, ErrPrecisionLoss
	}
	quota, _ := New(q._type, strconv.Itoa(q.value/2)+q.unit)
	return quota, nil
}

// Quarter 获取四分之一的资源配额（向下取整，最小值为1）
func (q *ResQuota) Quarter() *ResQuota {
	return q.Half().Half()
}

// Double 获取双倍的资源配额（最大值为对应种类资源上限）
func (q *ResQuota) Double() *ResQuota {
	val := lo.Min([]int{q.value * 2, lo.Ternary[int](q._type == CPU, maxCPU, maxMemory)})
	quota, _ := New(q._type, strconv.Itoa(val)+q.unit)
	return quota
}

// RealDouble 获取真正的双倍配额，如果超过限制，抛出 error
func (q *ResQuota) RealDouble() (*ResQuota, error) {
	if q.value*2 > lo.Ternary[int](q._type == CPU, maxCPU, maxMemory) {
		return nil, fmt.Errorf("%w: exceed max limit", ErrExceedLimit)
	}
	quota, _ := New(q._type, strconv.Itoa(q.value*2)+q.unit)
	return quota, nil
}

// 将原始字符串切分为值与单位
func (q *ResQuota) format() (err error) {
	unitStartAt := 0
	for _, r := range q.raw {
		if r == '.' {
			return fmt.Errorf("%w: decimals are not supported", ErrUnsupported)
		}
		if !unicode.IsDigit(r) {
			break
		}
		unitStartAt++
	}
	q.unit = q.raw[unitStartAt:]
	if q.value, err = strconv.Atoi(q.raw[:unitStartAt]); err != nil {
		return err
	}

	// 统一 CPU 单位为 m，内存单位为 Mi
	if q._type == CPU && q.unit == NoUnit {
		q.value, q.unit = q.value*1000, UnitM
	} else if q._type == Memory && q.unit == UnitGi {
		q.value, q.unit = q.value*1024, UnitMi
	}
	return nil
}

// 按照规则检查是否符合规范
func (q *ResQuota) validate() error {
	if q._type == CPU {
		// 1. 单位检查
		if !lo.Contains[string](cpuSupportedUnits, q.unit) {
			return fmt.Errorf("%w: please use %v as unit", ErrUnsupported, cpuSupportedUnits)
		}
		// 2. Limit 检查
		if q.value > maxCPU {
			return fmt.Errorf("%w: exceed cpu max limit %dm", ErrExceedLimit, maxCPU)
		}
	}

	if q._type == Memory {
		if !lo.Contains[string](memorySupportedUnits, q.unit) {
			return fmt.Errorf("%w: please use %v as unit", ErrUnsupported, memorySupportedUnits)
		}
		if q.value > maxMemory {
			return fmt.Errorf("%w: exceed memory max limit %dMi", ErrExceedLimit, maxMemory)
		}
	}
	return nil
}
