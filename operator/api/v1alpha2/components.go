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

package v1alpha2

import (
	"encoding/json"

	"github.com/pkg/errors"
	"k8s.io/apimachinery/pkg/runtime"

	components "bk.tencent.com/paas-app-operator/pkg/components/manager"
)

// Component is used to specify process component
type Component struct {
	// Name of component
	Name string `json:"name"`
	// Version of component
	Version string `json:"version"`
	// Properties of component
	Properties runtime.RawExtension `json:"properties,omitempty"`
}

func (c *Component) validate() error {
	manager, err := components.NewComponentLoader()
	if err != nil {
		return errors.Wrap(err, "new component mgr")
	}
	componentInfo, err := manager.GetComponentInfo(c.Name, c.Version)
	if err != nil || componentInfo == nil {
		return errors.Wrap(err, "can not find component")
	}
	var paramValues map[string]any
	if len(c.Properties.Raw) > 0 {
		if err = json.Unmarshal(c.Properties.Raw, &paramValues); err != nil {
			return errors.Wrap(err, "invalid properties")
		}
	} else {
		paramValues = make(map[string]any)
	}
	return manager.ValidateSchema(c.Name, c.Version, paramValues)
}
