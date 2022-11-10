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

package reconcilers

import (
	"context"
	"fmt"

	"github.com/samber/lo"
	"k8s.io/apimachinery/pkg/api/errors"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

type nameAccessor interface {
	GetName() string
}

// FindExtraByName filter the `input` slice, take items whose "name(by GetName()
// method)" can't be found in base slice.
func FindExtraByName[T nameAccessor](input []T, base []T) []T {
	// Make an index
	names := make(map[string]struct{})
	for _, obj := range base {
		names[obj.GetName()] = struct{}{}
	}

	return lo.Filter(input, func(item T, _ int) bool {
		_, ok := names[item.GetName()]
		return !ok
	})
}

// updateHandler should implement the object update policy
type updateHandler[T client.Object] func(ctx context.Context, cli client.Client, current T, want T) error

// alwaysUpdate will always update the current object
func alwaysUpdate[T client.Object](ctx context.Context, cli client.Client, current T, want T) error {
	if err := cli.Update(ctx, want); err != nil {
		return fmt.Errorf(
			"failed to update %s(%s): %w",
			want.GetObjectKind().GroupVersionKind().String(),
			want.GetName(),
			err,
		)
	}
	return nil
}

// UpsertObject will create the `obj T` if not exists, or update it by the updateHandler.
//
// It uses a common pattern to accept both value and pointer type parameters, see:
// https://go.googlesource.com/proposal/+/refs/heads/master/design/43651-type-parameters.md#pointer-method-example
// for details.
func UpsertObject[T any, PT interface {
	client.Object
	*T
}](
	ctx context.Context,
	cli client.Client,
	obj PT,
	updateHandler updateHandler[PT],
) error {
	exists := PT(new(T))
	if err := cli.Get(ctx, client.ObjectKeyFromObject(obj), exists); err != nil {
		// 获取失败，且不是不存在，直接退出
		if !errors.IsNotFound(err) {
			return err
		}
		// 资源在集群中不存在，创建资源
		if err = cli.Create(ctx, obj); err != nil {
			return fmt.Errorf(
				"failed to create %s(%s): %w",
				obj.GetObjectKind().GroupVersionKind().String(),
				obj.GetName(),
				err,
			)
		}
	} else {
		if updateHandler == nil {
			updateHandler = alwaysUpdate[PT]
		}
		// 集群资源存在, 且命中更新策略时, 更新资源
		return updateHandler(ctx, cli, exists, obj)
	}
	return nil
}
