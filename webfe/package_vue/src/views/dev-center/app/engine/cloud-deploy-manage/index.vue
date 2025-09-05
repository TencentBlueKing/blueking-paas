<template>
  <div class="right-main cloud-deploy-management-container">
    <!-- 部署历史 -->
    <div
      class="ps-top-bar"
      v-if="isDeployHistory"
    >
      <div class="top-title flex-row align-items-center">
        <i
          class="paasng-icon paasng-arrows-left icon-cls-back mr5"
          @click="goBack"
        />
        <h3>{{ $t('部署历史') }}</h3>
      </div>
    </div>
    <cloud-app-top-bar
      v-else
      :title="$t('部署管理')"
      :active="active"
      :nav-list="panels"
      :module-id="curModuleId"
      :right-title="$t('部署历史')"
      @change="handleTabChange"
      @right-config-click="toDeployHistory"
    >
      <template
        slot="title"
        v-if="isSmartApp && smartConfig.replicasPolicy"
      >
        <!-- s-mart 应用，副本数策略规则 -->
        <div class="top-bar-title flex-row align-items-center">
          <div>{{ $t('部署管理') }}</div>
          <div class="title-info flex-row align-items-center ml-12 pl-12">
            <div class="dropdown-trigger-content">
              <span>{{ $t('副本数策略') }}：{{ currentReplicasPolicy.label }}</span>
              <!-- 副本策略弹窗 -->
              <CustomPopconfirm
                width="300"
                trigger="click"
                placement="bottom-start"
                ext-cls="replicas-policy-popconfirm-cls"
                @confirm="changeReplicasPolicy"
              >
                <i
                  class="paasng-icon paasng-edit-2 ml5"
                  @click="initTempReplicasPolicy"
                ></i>
                <div
                  slot="content"
                  class="custom-popconfirm-content"
                >
                  <div class="custom-title">{{ $t('副本数策略') }}</div>
                  <div slot="content">
                    <bk-radio-group
                      v-model="tempReplicasPolicy"
                      class="flex-row flex-column"
                    >
                      <div
                        v-for="(item, index) in smartConfig.options"
                        :key="item.value"
                        :class="{ 'mt-8': index > 0 }"
                      >
                        <bk-radio
                          :value="item.value"
                          class="ml0 f12"
                          v-bk-tooltips.right="{ content: item.tips, width: 300 }"
                        >
                          {{ item.label }}
                        </bk-radio>
                      </div>
                    </bk-radio-group>
                  </div>
                </div>
              </CustomPopconfirm>
            </div>
            <div
              class="tips ml-12 text-ellipsis"
              v-bk-overflow-tips
            >
              <i class="paasng-icon paasng-info-line"></i>
              {{ currentReplicasPolicy.tips }}
            </div>
          </div>
        </div>
      </template>
    </cloud-app-top-bar>
    <div class="router-container m20">
      <router-view
        :key="routeIndex"
        :environment="active"
      ></router-view>
    </div>
  </div>
</template>
<script>
import appBaseMixin from '@/mixins/app-base-mixin';
import cloudAppTopBar from '@/components/cloud-app-top-bar.vue';
import CustomPopconfirm from '@/components/custom-popconfirm';

export default {
  name: 'CloudDeployManagement',
  components: {
    cloudAppTopBar,
    CustomPopconfirm,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      active: 'stag',
      routeIndex: 0,
      panels: [
        { name: 'stag', label: this.$t('预发布环境'), routeName: 'cloudAppDeployManageStag' },
        { name: 'prod', label: this.$t('生产环境'), routeName: 'cloudAppDeployManageProd' },
      ],
      smartConfig: {
        replicasPolicy: '',
        options: [
          {
            value: 'web_form_priority',
            label: this.$t('以页面配置为准'),
            tips: this.$t('重新部署时，忽略 S-mart 包中的副本数，保持当前线上副本数不变。'),
          },
          {
            value: 'app_desc_priority',
            label: this.$t('以应用描述文件为准'),
            tips: this.$t('重新部署时，进程副本数恢复为 S-mart 包中定义的数量。如未指定，则使用页面上的副本数。'),
          },
        ],
      },
      // 弹窗中临时选择的副本数策略
      tempReplicasPolicy: '',
    };
  },
  computed: {
    isDeployHistory() {
      return this.$route.meta.history;
    },
    currentReplicasPolicy() {
      return this.smartConfig.options.find((item) => item.value === this.smartConfig.replicasPolicy);
    },
  },
  watch: {
    $route() {
      this.routeIndex += 1;
    },
    appCode: {
      handler() {
        if (this.isSmartApp) {
          this.getAppDeployOptions();
        }
      },
      immediate: true,
    },
  },
  created() {
    // 判断当前来的环境
    this.active = this.$route.name === 'cloudAppDeployManageProd' ? 'prod' : 'stag';
  },
  methods: {
    handleTabChange(name) {
      this.active = name;
      const curEnv = this.panels.find((item) => item.name === name);
      this.$router.push({
        name: curEnv.routeName,
      });
    },

    /** 部署历史 */
    toDeployHistory() {
      this.$router.push({
        name: 'cloudAppDeployHistory',
      });
    },

    goBack() {
      this.$router.push({
        name: 'cloudAppDeployManageStag',
        params: {
          id: this.appCode,
        },
      });
    },

    changeReplicasPolicy() {
      if (this.smartConfig.replicasPolicy !== this.tempReplicasPolicy) {
        this.smartConfig.replicasPolicy = this.tempReplicasPolicy;
        this.updateAppDeployOptions();
      }
    },

    // 初始化弹窗中的临时选择值
    initTempReplicasPolicy() {
      this.tempReplicasPolicy = this.smartConfig.replicasPolicy;
    },

    // 获取应用副本数策略
    async getAppDeployOptions() {
      try {
        const { replicas_policy = 'web_form_priority' } = await this.$store.dispatch('deploy/getAppDeployOptions', {
          appCode: this.appCode,
        });
        this.smartConfig.replicasPolicy = replicas_policy;
        this.tempReplicasPolicy = replicas_policy;
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },

    // 更新应用副本数策略
    async updateAppDeployOptions() {
      try {
        await this.$store.dispatch('deploy/updateAppDeployOptions', {
          appCode: this.appCode,
          data: {
            replicas_policy: this.smartConfig.replicasPolicy,
          },
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('更新应用副本数策略成功'),
        });
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
  },
};
</script>
<style lang="scss" scoped>
.right-main {
  .top-title {
    padding-left: 20px;
    h3 {
      font-size: 16px;
      color: #313238;
      font-weight: 400;
      margin-left: 4px;
    }
    .icon-cls-back {
      color: #3a84ff;
      font-size: 20px;
      font-weight: bold;
      cursor: pointer;
    }
  }
  .top-bar-title {
    .title-info {
      font-size: 12px;
      color: #4d4f56;
      border-left: 1px solid #c4c6cc;
      .dropdown-trigger-content {
        i {
          cursor: pointer;
          transform: translateY(0px);
        }
        &:hover i {
          color: #3a84ff;
        }
      }
      .tips {
        max-width: 650px;
        color: #979ba5;
      }
    }
  }
}
.cloud-deploy-management-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.cloud-deploy-management {
  padding-top: 0px;
  margin: 0;
  margin-top: 0 !important;
}
.router-container {
  height: 100%;
}
.custom-popconfirm-content {
  .custom-title {
    font-size: 16px;
    color: #313238;
    line-height: 24px;
    margin-bottom: 12px;
  }
}
</style>
