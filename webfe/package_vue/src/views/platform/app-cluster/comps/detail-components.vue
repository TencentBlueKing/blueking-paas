<template>
  <div
    class="detail-components-container"
    v-bkloading="{ isLoading: isLoading, zIndex: 10 }"
  >
    <div class="view-title">{{ $t('安装信息') }}</div>
    <DetailsRow
      v-for="(val, key) in installInfoKeys"
      :label-width="126"
      :key="key"
    >
      <template slot="label">
        <div v-if="key === 'name'">
          {{ val }}
          <i
            class="paasng-icon paasng-info-line"
            v-bk-tooltips="{
              content: $t('推荐使用的命名空间。如果集群组件是手动安装，请在组件详情中查看实际安装的命名空间。'),
              width: 200,
            }"
          ></i>
          <span>：</span>
        </div>
        <template v-else>{{ `${val}：` }}</template>
      </template>
      <template slot="value">--</template>
    </DetailsRow>
    <div class="view-title">{{ $t('组件详情') }}</div>
    <bk-tab
      :active.sync="tabActive"
      type="card"
      ext-cls="components-tab-cls"
      @tab-change="handleTabChange"
    >
      <bk-tab-panel
        v-for="(panel, index) in componentList"
        v-bind="panel"
        :key="index"
      ></bk-tab-panel>
      <!-- 四个默认组件定制 -->
      <section v-bkloading="{ isLoading: cardLoading, zIndex: 10 }">
        <DefaultComponentDetails
          v-if="!isLoading"
          :data="curActiveTabData"
          :detail-data="componentDetail"
        />
      </section>
    </bk-tab>
  </div>
</template>

<script>
import DetailsRow from '@/components/details-row';
import DefaultComponentDetails from './default-component-details.vue';
export default {
  name: 'DetailComponents',
  props: {
    data: {
      type: Object,
      default: () => {},
    },
  },
  components: {
    DetailsRow,
    DefaultComponentDetails,
  },
  data() {
    return {
      componentLoading: false,
      componentList: [],
      tabActive: '',
      isLoading: false,
      cardLoading: false,
      installInfoKeys: {
        name: this.$t('命名空间'),
        description: this.$t('镜像仓库'),
        cluster_source: this.$t('应用访问类型'),
        bcs_project_id: this.$t('应用域名'),
      },
      componentDetail: {},
    };
  },
  created() {
    this.init();
  },
  computed: {
    curActiveTabData() {
      return this.componentList.find((v) => v.name === this.tabActive) ?? {};
    },
  },
  methods: {
    init() {
      this.isLoading = true;
      this.getClusterComponents();
    },
    handleTabChange(name) {
      this.getComponentDetail(name);
    },
    // 获取集群组件列表
    async getClusterComponents() {
      try {
        const res = await this.$store.dispatch('tenant/getClusterComponents', { clusterName: this.data?.name });
        this.componentList = res.map((item) => {
          return {
            ...item,
            label: item.name,
          };
        });
      } catch (e) {
        this.catchErrorHandler(e);
        this.isLoading = false;
      }
    },
    // 获取集群组件详情
    async getComponentDetail(componentName) {
      this.cardLoading = true;
      try {
        const ret = await this.$store.dispatch('tenant/getComponentDetail', {
          clusterName: this.data?.name,
          componentName,
        });
        this.componentDetail = ret;
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.isLoading = false;
        this.cardLoading = false;
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.detail-components-container {
  .view-title {
    font-weight: 700;
    font-size: 14px;
    color: #313238;
    line-height: 22px;
    margin: 24px 0 12px 0;
    &:first-child {
      margin-top: 0;
    }
  }
  .paasng-info-line {
    font-size: 14px;
    color: #979ba5;
  }
  .components-tab-cls {
    /deep/ .bk-tab-section {
      background: #f5f7fa;
    }
    /deep/ .bk-tab-label-wrapper i.bk-tab-scroll-controller {
      border: none;
      height: 42px !important;
      line-height: 42px !important;
      &.disabled {
        box-shadow: 0 0 20px rgba(0, 0, 0, 0.2) !important;
      }
      &::before {
        line-height: 42px;
      }
    }
    /deep/ .bk-tab-header {
      background-color: #fff !important;
      .bk-tab-label-list {
        li.bk-tab-label-item {
          color: #4d4f56;
          background: #eaebf0;
          border-radius: 4px 4px 0 0;
          margin-right: 8px;
          &:last-child {
            margin-right: 0;
          }
          &.active {
            color: #3a84ff;
            background: #f5f7fa;
          }
          &::after,
          &::before {
            width: 0 !important;
          }
        }
      }
    }
  }
}
</style>
