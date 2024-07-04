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

package resources

import (
	"strconv"

	"github.com/pkg/errors"
	"github.com/samber/lo"
	"github.com/tidwall/sjson"
	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	kuberuntime "k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/runtime/schema"
	logf "sigs.k8s.io/controller-runtime/pkg/log"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/common"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/common/labels"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/common/names"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/envs"
	"bk.tencent.com/paas-app-operator/pkg/controllers/bkapp/processes/volumes"
	"bk.tencent.com/paas-app-operator/pkg/kubeutil"
)

const (
	// DeployRevisionHistoryLimit 更新 Deployment 时不保留旧 ReplicasSet
	DeployRevisionHistoryLimit = int32(0)

	// DefaultImage 是当无法获取进程镜像时使用的默认镜像
	DefaultImage = "busybox:latest"

	// DefaultDeployID is the value that will be used if the DeployID is not set
	DefaultDeployID = "0"
)

// log is for logging in this package.
var log = logf.Log.WithName("controllers-resources")

// BuildProcDeployment build a deployment resource according to a bkapp's process declaration.
func BuildProcDeployment(app *paasv1alpha2.BkApp, procName string) (*appsv1.Deployment, error) {
	deployID := app.Status.DeployId
	if deployID == "" {
		deployID = DefaultDeployID
	}

	// Prepare data
	envVars := common.GetAppEnvs(app)
	mounterMap, err := volumes.GetAllVolumeMounterMap(app)
	if err != nil {
		return nil, err
	}
	replicasGetter := envs.NewReplicasGetter(app)
	useCNB, _ := strconv.ParseBool(app.Annotations[paasv1alpha2.UseCNBAnnoKey])

	// Find the process spec object
	proc, found := lo.Find(app.Spec.Processes, func(p paasv1alpha2.Process) bool { return p.Name == procName })
	if !found {
		return nil, errors.Errorf("process %s not found", procName)
	}

	// Start to build the deployment resource and return
	selector := labels.PodSelector(app, proc.Name)
	objLabels := labels.Deployment(app, proc.Name)

	// TODO: Add error handling
	image, pullPolicy, err := paasv1alpha2.NewProcImageGetter(app).Get(proc.Name)
	if err != nil {
		log.Info("Failed to get image for process %s: %v, use default values.", proc.Name, err)
		image = DefaultImage
		pullPolicy = corev1.PullIfNotPresent
	}

	// Get resource requirements
	resGetter := envs.NewProcResourcesGetter(app)
	resReq, err := resGetter.GetByProc(proc.Name)
	if err != nil {
		log.Info("Failed to get resources for process %s: %v, use default values.", proc.Name, err)
		resReq = resGetter.Default()
	}

	// Build annotations
	bkAppJson, err := getSerializedBkApp(app)
	if err != nil {
		return nil, errors.Wrapf(err, "serialize bkapp %s error", app.Name)
	}
	annotations := map[string]string{
		paasv1alpha2.DeployIDAnnoKey:                  deployID,
		paasv1alpha2.LastSyncedSerializedBkAppAnnoKey: string(bkAppJson),
	}

	deployment := &appsv1.Deployment{
		TypeMeta: metav1.TypeMeta{
			APIVersion: "apps/v1",
			Kind:       "Deployment",
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:        names.Deployment(app, proc.Name),
			Namespace:   app.Namespace,
			Labels:      objLabels,
			Annotations: annotations,
			OwnerReferences: []metav1.OwnerReference{
				*metav1.NewControllerRef(app, schema.GroupVersionKind{
					Group:   paasv1alpha2.GroupVersion.Group,
					Version: paasv1alpha2.GroupVersion.Version,
					Kind:    paasv1alpha2.KindBkApp,
				}),
			},
		},
		Spec: appsv1.DeploymentSpec{
			Selector:             &metav1.LabelSelector{MatchLabels: selector},
			RevisionHistoryLimit: lo.ToPtr(DeployRevisionHistoryLimit),
			Replicas:             replicasGetter.GetByProc(proc.Name),
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{
					Labels:      objLabels,
					Annotations: map[string]string{paasv1alpha2.DeployIDAnnoKey: deployID},
				},
				Spec: corev1.PodSpec{
					DNSConfig:        buildDNSConfig(app),
					HostAliases:      buildHostAliases(app),
					Containers:       buildContainers(proc, envVars, image, pullPolicy, resReq, useCNB),
					ImagePullSecrets: BuildImagePullSecrets(app),
					// 不默认向 Pod 中挂载 ServiceAccount Token
					AutomountServiceAccountToken: lo.ToPtr(false),
				},
			},
		},
	}

	for _, mounter := range mounterMap {
		err = mounter.ApplyToDeployment(app, deployment)
		if err != nil {
			log.Error(err, "Failed to inject mounts info to process", "process", proc.Name)
		}
	}

	return deployment, nil
}

// buildContainers 根据配置生产对应容器配置列表（目前设计单个 proc 只会有单个容器）
//
// - proc: 应用定义的进程对象
// - envs: 环境变量列表
// - image: 进程的镜像地址
// - pullPolicy: 镜像拉取策略
// - resRequirements: 容器资源限制
func buildContainers(
	proc paasv1alpha2.Process,
	envs []corev1.EnvVar,
	image string,
	pullPolicy corev1.PullPolicy,
	resRequirements corev1.ResourceRequirements,
	useCNB bool,
) []corev1.Container {
	var command, args []string
	if useCNB {
		// cnb 运行时启动 Process 的 entrypoint 是 `Process.Name`, command 是空列表
		// See: https://github.com/buildpacks/lifecycle/blob/main/cmd/launcher/cli/launcher.go
		command = append(command, proc.Name)
	} else {
		command = proc.Command
		args = proc.Args
	}

	container := corev1.Container{
		Name:            proc.Name,
		Image:           image,
		Resources:       resRequirements,
		ImagePullPolicy: pullPolicy,
		Env:             envs,
		Command:         kubeutil.ReplaceCommandEnvVariables(command),
		Args:            kubeutil.ReplaceCommandEnvVariables(args),
	}
	if proc.TargetPort != 0 {
		container.Ports = []corev1.ContainerPort{{ContainerPort: proc.TargetPort}}
	}
	// 容器探针
	if proc.Probes != nil {
		container.LivenessProbe = proc.Probes.Liveness
		container.ReadinessProbe = proc.Probes.Readiness
		container.StartupProbe = proc.Probes.Startup
	}
	return []corev1.Container{container}
}

// BuildImagePullSecrets 返回拉取镜像的 Secrets 列表
func BuildImagePullSecrets(app *paasv1alpha2.BkApp) []corev1.LocalObjectReference {
	pullSecretName := app.GetAnnotations()[paasv1alpha2.ImageCredentialsRefAnnoKey]
	switch pullSecretName {
	case "":
		return nil
	case "true":
		// 兼容支持多模块前的注解值
		// 历史版本使用 `true` 表示 image pull secret 已由 PaaS 创建, secret 名称约定为 $LegacyImagePullSecretName
		pullSecretName = paasv1alpha2.LegacyImagePullSecretName
	}
	// DefaultImagePullSecretName 由 workloads 服务负责创建
	return []corev1.LocalObjectReference{
		{
			Name: pullSecretName,
		},
	}
}

// Build the DNSConfig object for the application
func buildDNSConfig(app *paasv1alpha2.BkApp) *corev1.PodDNSConfig {
	if app.Spec.DomainResolution == nil {
		return nil
	}
	if servers := app.Spec.DomainResolution.Nameservers; len(servers) > 0 {
		return &corev1.PodDNSConfig{Nameservers: servers}
	}
	return nil
}

// Build the HostAliases object for the application
func buildHostAliases(app *paasv1alpha2.BkApp) (results []corev1.HostAlias) {
	if app.Spec.DomainResolution == nil {
		return nil
	}
	if aliases := app.Spec.DomainResolution.HostAliases; len(aliases) > 0 {
		for _, alias := range aliases {
			results = append(results, corev1.HostAlias{IP: alias.IP, Hostnames: alias.Hostnames})
		}
		return results
	}
	return nil
}

// Get the serialized bkapp object, use JSON format, some fields such as status are removed.
func getSerializedBkApp(bkapp *paasv1alpha2.BkApp) (string, error) {
	bkAppJson, err := kuberuntime.Encode(unstructured.UnstructuredJSONScheme, bkapp)
	if err != nil {
		return "", err
	}

	// Remove some field because it's not part of the specification
	data := string(bkAppJson)
	data, _ = sjson.Delete(data, "status")
	data, _ = sjson.Delete(data, "metadata.managedFields")
	return data, nil
}
