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

/**
 * 插件基础信息
 */

function BKStepsAdaptor (allStages) {
  return allStages.map((e, i) => {
    e.stage_id = e.id;
    e.icon = i + 1;
    e.title = e.name;
    return e;
  });
}

export default {
  data () {
    return {
      winHeight: 300
    };
  },
  computed: {
    pdId () {
      return this.$route.params.pluginTypeId;
    },
    pluginId () {
      return this.$route.params.id;
    },
    curPluginInfo () {
      return this.$store.state.plugin.curPluginInfo;
    },
    pluginFeatureFlags () {
      return this.$store.state.plugin.pluginFeatureFlags;
    },
    // 当前页面正在查看的发布版本, 并非 ongoing_release
    curRelease () {
      return this.$store.state.plugin.curRelease;
    },
    // 当前页面正在查看的发布版本的所有步骤
    curAllStages () {
      return BKStepsAdaptor(this.curRelease.all_stages || []);
    }
  },
  mounted () {
    this.winHeight = window.innerHeight;
  }
};
