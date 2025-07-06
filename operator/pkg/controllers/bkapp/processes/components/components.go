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
	"context"
	"encoding/json"
	"text/template"

	"github.com/pkg/errors"

	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/util/strategicpatch"
	"sigs.k8s.io/controller-runtime/pkg/client"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
)

const (
	// TEMPLATE_NAMESPACE 进程组件模板所在命名空间
	TEMPLATE_NAMESPACE = "bkapp-proc-component-tpl"
)

// ComponentsMutator inject component to deployment
type ComponentsMutator struct {
	component paasv1alpha2.Component
	client    client.Client
}

// PatchToDeployment inject component to deployment
func (c *ComponentsMutator) PatchToDeployment(ctx context.Context, deployment *appsv1.Deployment) error {
	patchBytes, err := c.getTemplate(ctx)
	if err != nil {
		return errors.Wrapf(err, "get template %s:%s", c.component.Type, c.component.Version)
	}

	originalBytes, err := json.Marshal(deployment)
	if err != nil {
		return errors.Wrap(err, "json marshal deployment")
	}
	patchedBytes, err := strategicpatch.StrategicMergePatch(originalBytes, patchBytes, appsv1.Deployment{})
	if err != nil {
		return errors.Wrap(err, "strategic merge patch")
	}

	if err = json.Unmarshal(patchedBytes, deployment); err != nil {
		return errors.Wrap(err, "json unmarshal deployment")
	}

	return nil
}

// getTemplate get component template from configmap
func (c *ComponentsMutator) getTemplate(ctx context.Context) ([]byte, error) {
	configMap := &corev1.ConfigMap{}
	if err := c.client.Get(ctx, client.ObjectKey{
		Namespace: TEMPLATE_NAMESPACE,
		Name:      c.component.Type,
	}, configMap); err != nil {
		return nil, err
	}

	// 从 ConfigMap 中获取对应版本的模板
	tpl, exists := configMap.Data[c.component.Version]
	if !exists {
		return nil, errors.Errorf("version %s not found in ConfigMap %s", c.component.Version, c.component.Type)
	}

	// 渲染模板
	tplBytes, err := c.renderTemplate(tpl)
	if err != nil {
		return nil, errors.Wrap(err, "render component template")
	}
	return tplBytes, nil
}

// renderTemplate render component template using params
func (c *ComponentsMutator) renderTemplate(templateContent string) ([]byte, error) {
	tmpl, err := template.New("component").Parse(templateContent)
	if err != nil {
		return nil, err
	}

	var paramValues map[string]interface{}
	if len(c.component.Properties.Raw) > 0 {
		if err = json.Unmarshal(c.component.Properties.Raw, &paramValues); err != nil {
			return nil, err
		}
	} else {
		paramValues = make(map[string]interface{})
	}

	var buf bytes.Buffer
	if err = tmpl.Execute(&buf, paramValues); err != nil {
		return nil, err
	}

	return buf.Bytes(), nil
}

// PatchAllComponentToDeployment patch all components to deployment
func PatchAllComponentToDeployment(
	client client.Client,
	ctx context.Context,
	proc *paasv1alpha2.Process,
	deployment *appsv1.Deployment,
) error {
	components := proc.Components
	for _, component := range components {
		configMapBasedComponent := &ComponentsMutator{
			component: component,
			client:    client,
		}
		err := configMapBasedComponent.PatchToDeployment(ctx, deployment)
		if err != nil {
			return err
		}
	}
	return nil
}
