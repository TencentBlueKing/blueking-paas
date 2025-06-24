<template>
  <bk-sideslider
    :is-show.sync="sidesliderVisible"
    :quick-close="true"
    show-mask
    width="640"
    ext-cls="detail-repository-sideslider-cls"
    @shown="shown"
    @hidden="reset"
  >
    <div slot="header">
      <div class="header-box">
        <span>{{ $t('代码库配置') }}</span>
      </div>
    </div>
    <div
      class="sideslider-content"
      slot="content"
    >
      <bk-tab
        :active.sync="tabActive"
        type="card"
        ext-cls="paas-custom-tab-card-grid"
      >
        <bk-tab-panel
          v-for="(panel, index) in panels"
          v-bind="panel"
          :key="index"
        ></bk-tab-panel>
        <div
          v-bkloading="{ isLoading: contentLoading, zIndex: 10 }"
          class="tab-content"
        >
          <RepositoryDetail
            :data="detail"
            :tab-active="tabActive"
          />
        </div>
      </bk-tab>
    </div>
  </bk-sideslider>
</template>

<script>
import RepositoryDetail from './components/repository-detail.vue';

export default {
  name: 'DetailRepositoryConfig',
  components: {
    RepositoryDetail,
  },
  props: {
    show: {
      type: Boolean,
      default: false,
    },
    id: {
      type: Number,
      default: -1,
    },
  },
  data() {
    return {
      contentLoading: false,
      detail: {},
      tabActive: 'baseInfo',
      panels: [
        { name: 'baseInfo', label: this.$t('基本信息') },
        { name: 'oauth', label: this.$t('OAuth 授权信息') },
        { name: 'display', label: this.$t('展示信息') },
      ],
    };
  },
  computed: {
    sidesliderVisible: {
      get: function () {
        return this.show;
      },
      set: function (val) {
        this.$emit('update:show', val);
      },
    },
  },
  methods: {
    shown() {
      this.getRepositoryDetail();
    },
    reset() {
      this.tabActive = 'baseInfo';
      this.detail = {};
    },
    // 获取代码库详情
    async getRepositoryDetail() {
      try {
        this.contentLoading = true;
        const ret = await this.$store.dispatch('tenantConfig/getRepositoryDetail', {
          id: this.id,
        });
        this.detail = ret;
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.contentLoading = false;
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.detail-repository-sideslider-cls {
  .sideslider-content {
    padding-top: 16px;
    background-color: #f5f7fa;
  }
  /deep/ .bk-tab-header {
    padding-left: 40px;
    background: #f5f7fa;
  }
  /deep/ .bk-tab-section {
    border: none;
    background-color: #fff;
    padding: 16px 40px;
  }
}
</style>
