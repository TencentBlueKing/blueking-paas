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

package kubetypes

import (
	"encoding/json"
	"regexp"
	"strings"

	"github.com/pkg/errors"

	"sigs.k8s.io/controller-runtime/pkg/client"
)

// GetJsonAnnotation gets the value of given key in the annotations, the data will be unmarshaled
// to the given type provided by the type parameter.
func GetJsonAnnotation[T any](obj client.Object, key string) (T, error) {
	var result T

	// Try to get the annotation and unmarshal it to the given type
	annots := obj.GetAnnotations()
	data, ok := annots[key]
	if !ok {
		return result, errors.New("not found")
	}
	err := json.Unmarshal([]byte(data), &result)
	return result, err
}

// SetJsonAnnotation sets the key to the given data in the annotations, the data wil be marshaled
// to JSON string before being set.
func SetJsonAnnotation(obj client.Object, key string, data interface{}) error {
	dataStr, err := json.Marshal(data)
	if err != nil {
		return err
	}

	// Set the annotation
	annots := obj.GetAnnotations()
	if annots == nil {
		annots = make(map[string]string)
	}
	annots[key] = string(dataStr)
	obj.SetAnnotations(annots)
	return nil
}

// The pattern that finds env variables(in BASH format)
var varPattern = regexp.MustCompile(`\$\{?([a-zA-Z_][a-zA-Z_0-9]*)\}?`)

// ReplaceCommandEnvVariables finds the environment variables in the command and args
// fields of the container spec, replace $FOO and ${FOO} with $(FOO) to make it works.
// See also: https://kubernetes.io/docs/tasks/inject-data-application/define-command-argument-container/#use-environment-variables-to-define-arguments
func ReplaceCommandEnvVariables(input []string) []string {
	var output []string
	for _, s := range input {
		// When the "dollar" character has been escaped, ignore it by replacing
		s = strings.Replace(s, "\\$", "\uFFFF", -1)
		s = varPattern.ReplaceAllString(s, "$$($1)")
		// Restore the escaped "dollar" character
		s = strings.Replace(s, "\uFFFF", "\\$", -1)
		output = append(output, s)
	}
	return output
}
