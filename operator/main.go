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

package main

import (
	"context"
	"flag"
	"net/http"
	"net/url"
	"os"
	"strconv"
	"time"

	"github.com/Tencent/bk-bcs/bcs-runtime/bcs-k8s/bcs-component/bcs-general-pod-autoscaler/pkg/metrics"
	"github.com/spf13/pflag"

	// Import all Kubernetes client auth plugins (e.g. Azure, GCP, OIDC, etc.)
	// to ensure that exec-entrypoint and run can make use of them.
	_ "k8s.io/client-go/plugin/pkg/client/auth"

	"github.com/getsentry/sentry-go"
	"github.com/iancoleman/strcase"
	"github.com/pkg/errors"
	"golang.org/x/time/rate"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/runtime/schema"
	utilruntime "k8s.io/apimachinery/pkg/util/runtime"
	clientgoscheme "k8s.io/client-go/kubernetes/scheme"
	"k8s.io/client-go/util/workqueue"
	ctrl "sigs.k8s.io/controller-runtime"
	cfg "sigs.k8s.io/controller-runtime/pkg/config/v1alpha1"
	"sigs.k8s.io/controller-runtime/pkg/controller"
	"sigs.k8s.io/controller-runtime/pkg/healthz"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"

	paasv1alpha1 "bk.tencent.com/paas-app-operator/api/v1alpha1"
	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/controllers"
	"bk.tencent.com/paas-app-operator/pkg/client"
	"bk.tencent.com/paas-app-operator/pkg/config"
	"bk.tencent.com/paas-app-operator/pkg/controllers/resources"
	"bk.tencent.com/paas-app-operator/pkg/platform/external"
	//+kubebuilder:scaffold:imports

	autoscaling "github.com/Tencent/bk-bcs/bcs-runtime/bcs-k8s/bcs-component/bcs-general-pod-autoscaler/pkg/apis/autoscaling/v1alpha1"
)

var (
	scheme   = runtime.NewScheme()
	setupLog = ctrl.Log.WithName("setup")
	cfgFile  string

	metricServerAddress string
	metricPort          uint
)

func init() {
	utilruntime.Must(clientgoscheme.AddToScheme(scheme))
	utilruntime.Must(paasv1alpha1.AddToScheme(scheme))
	utilruntime.Must(paasv1alpha2.AddToScheme(scheme))
	//+kubebuilder:scaffold:scheme

	pflag.StringVar(&metricServerAddress, "metric-server-address", "0.0.0.0", "http metric server address")
	pflag.UintVar(&metricPort, "metric-port", 10251, "prometheus metrics port")
}

func main() {
	flag.StringVar(&cfgFile, "config", "",
		"The controller will load its initial configuration from this file. "+
			"Omit this flag to use the default configuration values. "+
			"Command-line flags override configuration from this file.")
	opts := zap.Options{
		Development: true,
	}
	opts.BindFlags(flag.CommandLine)
	flag.Parse()

	ctrl.SetLogger(zap.New(zap.UseFlagOptions(&opts)))

	var err error
	projConf := paasv1alpha1.NewProjectConfig()
	options := ctrl.Options{
		Scheme:         scheme,
		LeaderElection: false,
	}
	if cfgFile != "" {
		options, err = options.AndFrom(ctrl.ConfigFile().AtPath(cfgFile).OfKind(projConf))
		if err != nil {
			setupLog.Error(err, "unable to load the config file")
			os.Exit(1)
		}
	}

	config.SetConfig(projConf)

	// Don't add autoscaling to scheme in init() as it is optional.
	if config.Global.IsAutoscalingEnabled() {
		utilruntime.Must(autoscaling.AddToScheme(scheme))
	}

	// TODO: This is not the desired way to use the global config, we should refactor
	// the code in current file to avoid type assertion entirely.
	cfgObj := config.Global.(*paasv1alpha1.ProjectConfig)

	// ref: how to usage sentry in go -> https://docs.sentry.io/platforms/go/usage/
	sentryDSN := cfgObj.Platform.SentryDSN
	if sentryDSN == "" {
		setupLog.Info("[Sentry] SentryDSN unset, all events waiting for report will be dropped.")
	}
	if err = sentry.Init(sentry.ClientOptions{Dsn: sentryDSN}); err != nil {
		setupLog.Error(err, "unable to set sentry dsn")
		os.Exit(1)
	}

	if err = initExtensionClient(); err != nil {
		setupLog.Error(err, "unable to init extension client")
		os.Exit(1)
	}

	initIngressPlugins()

	setupCtx := context.Background()
	mgr, err := ctrl.NewManager(ctrl.GetConfigOrDie(), options)
	if err != nil {
		setupLog.Error(err, "unable to start manager")
		os.Exit(1)
	}
	mgrCli := client.New(mgr.GetClient())
	mgrScheme := mgr.GetScheme()

	bkappMgrOpts := genGroupKindMgrOpts(paasv1alpha1.GroupKindBkApp, projConf.Controller)
	if err = controllers.NewBkAppReconciler(mgrCli, mgrScheme).
		SetupWithManager(setupCtx, mgr, bkappMgrOpts); err != nil {
		setupLog.Error(err, "unable to create controller", "controller", "BkApp")
		os.Exit(1)
	}
	dgmappingMgrOpts := genGroupKindMgrOpts(paasv1alpha1.GroupKindDomainGroupMapping, projConf.Controller)
	if err = controllers.NewDomainGroupMappingReconciler(mgrCli, mgrScheme).
		SetupWithManager(setupCtx, mgr, dgmappingMgrOpts); err != nil {
		setupLog.Error(err, "unable to create controller", "controller", "DomainGroupMapping")
		os.Exit(1)
	}
	if os.Getenv("ENABLE_WEBHOOKS") != "false" {
		if err = (&paasv1alpha1.BkApp{}).SetupWebhookWithManager(mgr); err != nil {
			setupLog.Error(err, "unable to create webhook", "webhook", "v1alpha1/BkApp")
			os.Exit(1)
		}
		if err = (&paasv1alpha1.DomainGroupMapping{}).SetupWebhookWithManager(mgr); err != nil {
			setupLog.Error(err, "unable to create webhook", "webhook", "DomainGroupMapping")
			os.Exit(1)
		}
		if err = (&paasv1alpha2.BkApp{}).SetupWebhookWithManager(mgr); err != nil {
			setupLog.Error(err, "unable to create webhook", "webhook", "v1alpha2/BkApp")
			os.Exit(1)
		}
	}

	// start metric server
	var metricsServer metrics.PrometheusMetricServer
	addr := metricServerAddress + ":" + strconv.Itoa(int(metricPort))
	go metricsServer.NewServer(addr, "/metrics")

	//+kubebuilder:scaffold:builder
	if err = mgr.AddHealthzCheck("healthz", healthz.Ping); err != nil {
		setupLog.Error(err, "unable to set up health check")
		os.Exit(1)
	}
	if err = mgr.AddReadyzCheck("readyz", healthz.Ping); err != nil {
		setupLog.Error(err, "unable to set up ready check")
		os.Exit(1)
	}

	setupLog.Info("starting manager")
	if err = mgr.Start(ctrl.SetupSignalHandler()); err != nil {
		setupLog.Error(err, "problem running manager")
		os.Exit(1)
	}
}

func initExtensionClient() error {
	cfgObj := config.Global.(*paasv1alpha1.ProjectConfig)

	if cfgObj.Platform.BkAPIGatewayURL != "" {
		bkpaasGatewayBaseURL, err := url.Parse(cfgObj.Platform.BkAPIGatewayURL)
		if err != nil {
			return errors.Wrap(err, "failed to parse bkpaas gateway url to net.Url")
		}
		external.SetDefaultClient(
			external.NewClient(
				bkpaasGatewayBaseURL,
				cfgObj.Platform.BkAppCode,
				cfgObj.Platform.BkAppSecret,
				http.DefaultClient,
			),
		)
	} else {
		setupLog.Info("PlatformConfig.BkAPIGateWayURL is not configured, some of Platform-related functionality will be limited")
	}
	return nil
}

func initIngressPlugins() {
	cfgObj := config.Global.(*paasv1alpha1.ProjectConfig)

	pluginCfg := cfgObj.IngressPlugin
	if pluginCfg.AccessControl != nil {
		setupLog.Info("[IngressPlugin] access control plugin enabled.")
		resources.RegistryPlugin(&resources.AccessControlPlugin{Config: pluginCfg.AccessControl})
	} else {
		setupLog.Info("[IngressPlugin] Missing access control config, disable access control feature.")
	}
	if pluginCfg.PaaSAnalysis != nil && pluginCfg.PaaSAnalysis.Enabled {
		// PA 无需额外配置, 可以总是启用该插件
		setupLog.Info("[IngressPlugin] PA(paas-analysis) plugin enabled.")
		resources.RegistryPlugin(&resources.PaasAnalysisPlugin{})
	} else {
		setupLog.Info("[IngressPlugin] Missing paas-analysis config or this cluster is not supported, disable PA feature.")
	}
}

// 生成某类组资源管理器配置
func genGroupKindMgrOpts(groupKind schema.GroupKind, ctrlCfg *cfg.ControllerConfigurationSpec) controller.Options {
	// 支持配置短路径，如 bkApp，若不存在，则获取 groupKind.String() 的值，如 BkApp.paas.bk.tencent.com
	concurrency, ok := ctrlCfg.GroupKindConcurrency[strcase.ToLowerCamel(groupKind.Kind)]
	if !ok {
		concurrency = ctrlCfg.GroupKindConcurrency[groupKind.String()]
	}
	return controller.Options{
		MaxConcurrentReconciles: concurrency,
		RateLimiter: workqueue.NewMaxOfRateLimiter(
			// 首次重试延迟 1s，后续指数级翻倍，最高延迟 300s
			workqueue.NewItemExponentialFailureRateLimiter(time.Second, 5*time.Minute),
			// 10 qps, 100 bucket size.  This is only for retry speed, and it's only the overall factor (not per item)
			&workqueue.BucketRateLimiter{Limiter: rate.NewLimiter(rate.Limit(10), 100)},
		),
	}
}
