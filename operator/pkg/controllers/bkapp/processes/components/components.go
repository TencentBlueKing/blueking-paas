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

package components

import (
	"bytes"
	"encoding/json"
	"text/template"

	"github.com/pkg/errors"
	"k8s.io/apimachinery/pkg/util/strategicpatch"
	"sigs.k8s.io/yaml"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	components "bk.tencent.com/paas-app-operator/pkg/components/manager"
	appsv1 "k8s.io/api/apps/v1"
)

// ComponentMutator inject component to deployment
type ComponentMutator struct {
	component     paasv1alpha2.Component
	defaultParams map[string]any
}

// PatchToDeployment inject component to deployment
func (c *ComponentMutator) patchToDeployment(deployment *appsv1.Deployment) error {
	patchBytes, err := c.getTemplate()
	if err != nil {
		return errors.Wrapf(err, "get template %s:%s", c.component.Name, c.component.Version)
	}
	originalBytes, err := json.Marshal(deployment)
	if err != nil {
		return errors.Wrap(err, "json marshal deployment")
	}
	patchJSONBytes, err := yaml.YAMLToJSON(patchBytes)
	if err != nil {
		return errors.Wrap(err, "component tpl yaml to json")
	}
	patchedBytes, err := strategicpatch.StrategicMergePatch(originalBytes, patchJSONBytes, appsv1.Deployment{})
	if err != nil {
		return errors.Wrap(err, "strategic merge patch")
	}
	if err = json.Unmarshal(patchedBytes, deployment); err != nil {
		return errors.Wrap(err, "json unmarshal deployment")
	}

	return nil
}

// getTemplate get component template from configmap
func (c *ComponentMutator) getTemplate() ([]byte, error) {
	manager, err := components.NewComponentLoader()
	if err != nil {
		return nil, err
	}
	tpl, err := manager.GetTemplate(c.component.Name, c.component.Version)
	if err != nil {
		return nil, err
	}
	// 渲染模板
	tplBytes, err := c.renderTemplate(string(tpl))
	if err != nil {
		return nil, errors.Wrap(err, "render component template")
	}
	return tplBytes, nil
}

// renderTemplate render component template using params
func (c *ComponentMutator) renderTemplate(templateContent string) ([]byte, error) {
	tmpl, err := template.New("component").Parse(templateContent)
	if err != nil {
		return nil, err
	}

	paramValues := make(map[string]any)
	for k, v := range c.defaultParams {
		paramValues[k] = v
	}

	if len(c.component.Properties.Raw) > 0 {
		if err = json.Unmarshal(c.component.Properties.Raw, &paramValues); err != nil {
			return nil, err
		}
	}

	var buf bytes.Buffer
	if err = tmpl.Execute(&buf, paramValues); err != nil {
		return nil, err
	}

	return buf.Bytes(), nil
}

// PatchToDeployment patch all components to deployment
func PatchToDeployment(
	proc *paasv1alpha2.Process,
	deployment *appsv1.Deployment,
) error {
	for _, component := range proc.Components {
		mutator := &ComponentMutator{
			component: component,
			defaultParams: map[string]any{
				"procName": proc.Name,
			},
		}
		err := mutator.patchToDeployment(deployment)
		if err != nil {
			return err
		}
	}
	return nil
}
