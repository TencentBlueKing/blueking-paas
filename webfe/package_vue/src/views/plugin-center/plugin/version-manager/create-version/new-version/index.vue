<template>
  <div class="plugin-new-version">
    <div class="new-version-container">
      <!-- 发布内容 -->
      <release-content
        v-bind="$attrs"
        ref="releaseContent"
      />
      <!-- 可见范围 -->
      <visible-range :data="visibleRangeData" />
      <!-- 发布策略 -->
      <release-strategy
        v-bind="$attrs"
        ref="releaseStrategy"
        @strategy-change="handleStrategyChange"
      />
    </div>
    <section class="version-tools">
      <div class="button-warpper">
        <bk-button
          :theme="'primary'"
          class="mr8"
          :loading="isSubmitLoading"
          @click="handleSubmit"
        >
          {{ curStrategyType === 'full' ? $t('申请全量发布') : $t('申请灰度发布') }}
        </bk-button>
        <bk-button
          :theme="'default'"
          type="submit"
          @click="handleBack('prod')"
        >
          {{ $t('取消') }}
        </bk-button>
      </div>
      <p
        class="release-tips"
        v-bk-overflow-tips
        v-dompurify-html="curStrategyType === 'full' ? officialReleaseTips : canaryReleaseTips"
      ></p>
    </section>
  </div>
</template>
<script>
import pluginBaseMixin from '@/mixins/plugin-base-mixin';
import releaseContent from './release-content.vue';
import visibleRange from './visible-range.vue';
import releaseStrategy from './release-strategy.vue';

export default {
  name: 'PluginNewVersion',
  components: {
    releaseContent,
    visibleRange,
    releaseStrategy,
  },
  mixins: [pluginBaseMixin],
  props: {
    loading: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      // 灰度 - 灰度发布审批中 - 灰度中 (审批通过) - 灰度中 (发布完成)
      releaseStep: '',
      isSubmitLoading: false,
      visibleRangeData: {
        bkci_project: [],
        organization: [],
      },
      curStrategyType: '',
    };
  },
  computed: {
    canaryReleaseTips() {
      return this.$t('灰度发布需由<em>工具管理员</em>进行审批。');
    },
    officialReleaseTips() {
      return this.$t('正式发布需由<em>平台管理员</em>进行审批。');
    },
  },
  created() {
    this.getVisibleRange();
  },
  methods: {
    // 新建正式版本
    async handleSubmit() {
      try {
        await Promise.all([this.$refs.releaseContent.validate(), this.$refs.releaseStrategy.validate()]);

        // 获取子组件数据
        const content = this.$refs.releaseContent.getFormData();
        const strategy = this.$refs.releaseStrategy.getFormData();
        const params = {
          ...content,
          release_strategy: {
            ...strategy,
          },
        };
        // 提交
        this.createVersion(params);
      } catch (e) {
        console.error(e);
      }
    },
    // 新建版本
    async createVersion(data) {
      this.isSubmitLoading = true;
      try {
        const res = await this.$store.dispatch('plugin/createVersion', {
          pdId: this.pdId,
          pluginId: this.pluginId,
          data,
        });
        this.$bkMessage({
          theme: 'success',
          message: this.$t('新建成功!'),
        });
        // 版本详情
        this.$router.push({
          name: 'pluginReleaseDetails',
          params: {
            pluginTypeId: this.pdId,
            id: this.pluginId,
          },
          query: {
            versionId: res.id,
          },
        });
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.isSubmitLoading = false;
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
    handleBack(type) {
      this.$router.push({
        name: 'pluginVersionManager',
        query: { type },
      });
    },
    handleStrategyChange(type) {
      this.curStrategyType = type;
    },
  },
};
</script>

<style lang="scss" scoped>
.plugin-new-version {
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
      flex-grow: 0;
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
}
</style>
