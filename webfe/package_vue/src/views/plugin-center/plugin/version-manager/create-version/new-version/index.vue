<template>
  <div class="plugin-new-version">
    <div class="new-version-container">
      <!-- 发布内容 -->
      <release-content ref="releaseContent" :scheme="scheme" />
      <!-- 发布策略 -->
      <release-strategy ref="releaseStrategy" :scheme="scheme" />
    </div>
    <section class="version-tools">
      <div class="button-warpper">
        <bk-button
          :theme="'primary'"
          class="mr8"
          :lodaing="isSubmitLoading"
          @click="handleSubmit"
        >
          {{ $t('申请灰度发布') }}
        </bk-button>
        <bk-button
          :theme="'default'"
          type="submit"
          @click="handleBack('prod')"
        >
          {{ $t('取消') }}
        </bk-button>
      </div>
      <p class="release-tips" v-html="releaseTips"></p>
    </section>
  </div>
</template>
<script>
import pluginBaseMixin from '@/mixins/plugin-base-mixin';
import releaseContent from './release-content.vue';
import releaseStrategy from './release-strategy.vue';

export default {
  name: 'PluginNewVersion',
  components: {
    releaseContent,
    releaseStrategy,
  },
  mixins: [pluginBaseMixin],
  props: {
    scheme: {
      type: Object,
      default: () => {},
    },
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
    };
  },
  computed: {
    releaseTips() {
      return this.$t('灰度发布需由<em>工具管理员</em>进行审批；若选择了灰度组织范围，还需要由<em>工具发布者的组长</em>同时进行审批。');
    },
  },
  created() {
    console.log('scheme', this.scheme);
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
        await this.$store.dispatch('plugin/createVersion', {
          pdId: this.pdId,
          pluginId: this.pluginId,
          data,
        });
        this.$bkMessage({
          theme: 'success',
          message: this.$t('新建成功!'),
        });
        // 版本管理
        this.$router.push({
          name: 'pluginVersionManager',
          query: {
            type: 'prod',
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
    handleBack(type) {
      this.$router.push({
        name: 'pluginVersionManager',
        query: { type },
      });
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
    left: 0;
    right: 0;
    bottom: 0;
    height: 48px;
    background: #fafbfd;
    box-shadow: 0 -1px 0 0 #dcdee5;
  }

  .release-tips {
    color: #979ba5;
    font-size: 12px;
    margin-left: 16px;
    /deep/ em {
      font-weight: 700;
    }
  }
  }
</style>
