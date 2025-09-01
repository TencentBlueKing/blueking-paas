<template>
  <div class="version-details-container">
    <paas-plugin-title
      :name="$t('版本发布')"
      :version-data="versionData"
      :status-map="CODECC_RELEASE_STATUS"
      :is-codecc="true"
    >
      <template slot="right" v-if="canTerminateStatus.includes(versionData.gray_status)">
        <bk-button @click="handleCodeccCancelReleases">
          <i class="paasng-icon paasng-minus-circle" />
          {{ $t('终止发布') }}
        </bk-button>
      </template>
    </paas-plugin-title>
    <!-- 版本发布 -->
    <paas-content-loader
      :is-loading="isLoading"
      placeholder="plugin-new-version-loading"
      class="app-container middle"
      :style="{ paddingBottom: !isFullReleaseSuccessful ? '48px' : '0' }"
    >
      <!-- 未通过 -->
      <bk-alert
        v-if="isApprovalFailed"
        class="warning-alert-cls mb16"
        type="error"
        :show-icon="false"
      >
        <div slot="title">
          <i class="paasng-icon paasng-remind"></i>
          <span v-if="approvalStatus === 'FINISHED'">
            {{ $t('审批未通过，请修改发布信息后重新申请') }}
          </span>
          <span v-else>
            {{ $t('单据{d}，请修改发布信息后重新申请', { d: versionData.latest_release_strategy?.ticket_info?.current_status_display }) }}
          </span>
          <bk-button
            size="small"
            text
            class="ml10"
            @click="viewApprovalDetails"
          >
            {{ $t('查看审批详情') }}
          </bk-button>
        </div>
      </bk-alert>
      <!-- 审批中 -->
      <bk-alert
        v-else-if="isUnderReview"
        class="warning-alert-cls mb16"
        type="warning"
        :show-icon="false"
      >
        <div slot="title">
          <i class="paasng-icon paasng-remind"></i>
          {{ $t('灰度发布审批中，请耐心等待') }}
          <bk-button
            size="small"
            text
            class="ml10"
            @click="viewApprovalDetails"
          >
            {{ $t('查看审批详情') }}
          </bk-button>
          <bk-button
            size="small"
            text
            class="ml10"
            @click="viewApprovalDetails"
          >
            {{ $t('撤销提单') }}
          </bk-button>
        </div>
      </bk-alert>
      <release-content
        ref="releaseContent"
        :mode="'view'"
        :data="versionData"
        :version-info="curVersionData"
      />
      <!-- 可见范围 -->
      <visible-range :data="visibleRangeData" />
      <release-strategy
        ref="releaseStrategy"
        :mode="releaseStrategyMode"
        :data="versionData"
        step="release"
        @strategy-change="handleStrategyChange"
      />
      <!-- 发布结果 -->
      <release-result :url="versionData.release_result_url" />
      <section
        class="version-tools"
        v-if="!isFullReleaseSuccessful"
      >
        <div
          class="button-warpper"
          v-if="!isRequestGrayRelease"
        >
          <!-- 审批失败，拒绝 -->
          <bk-button
            v-if="isApprovalFailed"
            :theme="'primary'"
            class="mr8"
            @click="handleReapply"
          >
            {{ $t('重新发布') }}
          </bk-button>
          <!-- 审批中 -->
          <bk-button
            v-else-if="isUnderReview"
            :theme="'default'"
            type="submit"
            :disabled="!versionData.latest_release_strategy?.ticket_info?.can_withdraw"
            @click="viewApprovalDetails"
          >
            {{ $t('撤销提单') }}
          </bk-button>
          <!-- 扩大灰度范围时，之前已选的项目/组织范围不可删除，只能增加 -->
          <template v-else>
            <bk-button
              :theme="'primary'"
              type="submit"
              @click="handleGrayscaleRange('full')"
            >
              {{ $t('申请全量发布') }}
            </bk-button>
            <bk-button
              :theme="'default'"
              type="submit"
              class="ml8"
              @click="handleGrayscaleRange('gray')"
            >
              {{ $t('扩大灰度范围') }}
            </bk-button>
          </template>
        </div>
        <template v-else>
          <div class="button-warpper">
            <bk-button
              :theme="'primary'"
              class="mr8"
              :loading="isApplyLoading"
              @click="handleSubmit"
            >
              {{ curStrategyType === 'full' ? $t('申请全量发布') : $t('申请扩大灰度范围') }}
            </bk-button>
            <bk-button
              :theme="'default'"
              type="submit"
              @click="handleCancel"
            >
              {{ $t('取消') }}
            </bk-button>
          </div>
          <p
            class="release-tips"
            v-bk-overflow-tips
            v-dompurify-html="curStrategyType === 'full' ? officialReleaseTips : canaryReleaseTips"
          ></p>
        </template>
      </section>
    </paas-content-loader>
  </div>
</template>

<script>
import paasPluginTitle from '@/components/pass-plugin-title';
import pluginBaseMixin from '@/mixins/plugin-base-mixin';
import releaseContent from '../create-version/new-version/release-content.vue';
import visibleRange from '../create-version/new-version/visible-range.vue';
import releaseStrategy from '../create-version/new-version/release-strategy.vue';
import releaseResult from '../create-version/new-version/release-result.vue';
import { CODECC_RELEASE_STATUS } from '@/common/constants';

export default {
  name: 'VersionDetails',
  components: {
    paasPluginTitle,
    releaseContent,
    visibleRange,
    releaseStrategy,
    releaseResult,
  },
  mixins: [pluginBaseMixin],
  data() {
    return {
      isLoading: true,
      versionData: {
        latest_release_strategy: {},
      },
      releaseStrategyMode: 'view',
      isRequestGrayRelease: false,
      isApplyLoading: false,
      CODECC_RELEASE_STATUS,
      visibleRangeData: {
        bkci_project: [],
        organization: [],
      },
      scheme: {
        source_versions: [],
      },
      canTerminateStatus: ['gray_approval_in_progress', 'full_approval_in_progress', 'in_gray'],
      curStrategyType: '',
    };
  },
  computed: {
    titleConfig() {
      return {};
    },
    versionId() {
      return this.$route.query.versionId;
    },
    canaryReleaseTips() {
      return this.$t('灰度发布需由<em>工具管理员</em>进行审批。');
    },
    officialReleaseTips() {
      return this.$t('正式发布需由<em>平台管理员</em>进行审批。');
    },
    // 审批失败要用 release 的 status 来判断
    releaseStatus() {
      return this.versionData.status;
    },
    approvalStatus() {
      return this.versionData.latest_release_strategy?.ticket_info?.current_status;
    },
    // 审批中
    isUnderReview() {
      return ['RUNNING', 'SUSPENDED'].includes(this.approvalStatus);
    },
    // 审批失败|中断
    isApprovalFailed() {
      return ['failed', 'interrupted'].includes(this.releaseStatus);
    },
    // 全量发布成功
    isFullReleaseSuccessful() {
      return this.releaseStatus === 'successful' && this.approvalStatus === 'FINISHED';
    },
    curVersionData() {
      return this.scheme.source_versions.find(v => v.name === this.versionData.source_version_name);
    },
  },
  created() {
    this.init();
  },
  methods: {
    init() {
      Promise.all([this.getReleaseDetail(), this.getVisibleRange(), this.getNewVersionFormat()]).finally(() => {
        this.isLoading = false;
      });
    },

    // 获取版本详情
    async getReleaseDetail(closeLoading = false) {
      this.isLoading = true;
      try {
        const res = await this.$store.dispatch('plugin/getReleaseDetail', {
          pdId: this.pdId,
          pluginId: this.pluginId,
          releaseId: this.versionId,
        });
        this.versionData = res;
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        if (closeLoading) {
          this.isLoading = false;
        }
      }
    },

    // 查看申请详情
    viewApprovalDetails() {
      const url = this.versionData.latest_release_strategy?.ticket_info?.ticket_url;
      window.open(url, '_blank');
    },

    handleGrayscaleRange(type) {
      // 只允许扩大灰度范围
      this.releaseStrategyMode = 'edit';
      this.isRequestGrayRelease = true;
      this.curStrategyType = type;
      if (type === 'full') {
        // 全量
        this.versionData.latest_release_strategy.strategy = 'full';
      } else {
        // 扩大灰度范围
        this.versionData.latest_release_strategy.strategy = 'gray';
      }
    },

    handleCancel() {
      this.releaseStrategyMode = 'view';
      this.isRequestGrayRelease = false;
    },

    // 申请灰度发布
    async handleSubmit() {
      try {
        await this.$refs.releaseStrategy.validate();

        // 获取子组件数据
        const formData = this.$refs.releaseStrategy.getFormData();
        const params = {
          strategy: formData.strategy,
          ...(formData.strategy === 'gray' && {
            // 仅在灰度
            bkci_project: formData.bkci_project,
            organization: formData.organization,
          }),
        };
        // 提交
        this.applyGrayRelease(params);
      } catch (e) {
        console.error(e);
      }
    },

    // 申请灰度发布（扩大灰度范围）
    async applyGrayRelease(data) {
      this.isApplyLoading = true;
      try {
        await this.$store.dispatch('plugin/expandGrayScope', {
          pdId: this.pdId,
          pluginId: this.pluginId,
          id: this.versionId,
          data,
        });
        // 重新请求当前详情-全量发布（成功）流程结束
        await this.getReleaseDetail(true);
        this.handleCancel();
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.isApplyLoading = false;
      }
    },

    // 获取可见范围数据
    async getVisibleRange() {
      try {
        const res = await this.$store.dispatch('plugin/getVisibleRange', {
          pdId: this.pdId,
          pluginId: this.pluginId,
        });
        this.visibleRangeData = res;
      } catch (e) {
        // 404 就说明没有数据
        if (e.status === 404) {
          return;
        }
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    // 获取schema
    async getNewVersionFormat() {
      try {
        const res = await this.$store.dispatch('plugin/getNewVersionFormat', {
          pdId: this.pdId,
          pluginId: this.pluginId,
          type: 'prod',
        });
        this.scheme = res;
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    // 重新发布
    handleReapply() {
      this.$router.push({
        name: 'pluginVersionEditor',
        params: {
          pluginTypeId: this.pdId,
          id: this.pluginId,
        },
        query: {
          type: 'prod',
          versionId: this.versionId,
        },
      });
    },

    // 终止发布版本
    handleCodeccCancelReleases() {
      this.$bkInfo({
        title: `${this.$t('确认终止发布版本')}${this.versionData.source_version_name} ？`,
        width: 540,
        maskClose: true,
        confirmLoading: true,
        confirmFn: async () => {
          try {
            await this.$store.dispatch('plugin/codeccCancelReleases', {
              pdId: this.pdId,
              pluginId: this.pluginId,
              releaseId: this.versionData.id,
            });
            this.$bkMessage({
              theme: 'success',
              message: this.$t('已终止当前的发布版本'),
            });
            this.$router.go(-1);
          } catch (e) {
            this.$bkMessage({
              theme: 'error',
              message: e.detail || e.message || this.$t('接口异常'),
            });
          } finally {
            return true;
          }
        },
      });
    },

    handleStrategyChange(type) {
      this.curStrategyType = type;
    },
  },
};
</script>

<style lang="scss" scoped>
.version-details-container {
  .version-tools {
    position: fixed;
    padding-left: 264px;
    display: flex;
    align-items: center;
    flex-wrap: nowrap;
    left: 0;
    right: 0;
    bottom: 0;
    height: 48px;
    z-index: 9;
    background: #fafbfd;
    box-shadow: 0 -1px 0 0 #dcdee5;
    .button-warpper {
      display: flex;
      flex-shrink: 0;
    }
  }
  .release-tips {
    color: #979ba5;
    font-size: 12px;
    margin-left: 16px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    /deep/ em {
      font-weight: 700;
    }
    /deep/ span {
      color: #ea3636;
    }
  }
  .mb16 {
    margin-bottom: 16px;
  }
  .ml8 {
    margin-left: 8px;
  }
  .warning-alert-cls {
    i {
      font-size: 14px;
      color: #ff9c01;
      transform: translateY(0px);
    }
    /deep/ .bk-alert-wraper {
      height: 32px;
      align-items: center;
      font-size: 12px;
      color: #63656e;
    }
    /deep/ .bk-button-text.bk-button-small {
      padding: 0;
    }
  }
}
</style>
