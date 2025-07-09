<template>
  <div class="detail-components-container">
    <!-- 安装信息编辑 -->
    <bk-button
      class="clustertab-edit-btn-cls"
      theme="primary"
      :outline="true"
      @click="handleEdit(2)"
    >
      {{ $t('编辑') }}
    </bk-button>
    <div class="view-title">{{ $t('安装信息') }}</div>
    <DetailsRow
      v-for="(val, key) in installInfoKeys"
      :label-width="labelWidth"
      :align="'flex-start'"
      :key="key"
    >
      <template slot="label">
        <div v-if="key === 'component_preferred_namespace'">
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
      <template slot="value">
        <div v-if="key === 'app_domains'">
          <template v-if="!data[key]?.length">--</template>
          <div
            v-else
            v-for="(item, i) in data[key]"
            :key="i"
          >
            {{ `${item.name}（${item.https_enabled ? $t('启用') : $t('不启用')} HTTPS）` }}
          </div>
        </div>
        <span v-else>
          {{ (key === 'app_address_type' ? pathMap[data[key]] : data[key]) || '--' }}
        </span>
      </template>
    </DetailsRow>
    <div v-bkloading="{ isLoading: isLoading, zIndex: 10 }">
      <div class="view-title comps-details">
        {{ $t('组件详情') }}
        <!-- 组件安装编辑 -->
        <bk-button
          v-if="componentList.length"
          theme="primary"
          :outline="true"
          @click="handleEdit(3)"
        >
          {{ $t('管理') }}
        </bk-button>
      </div>
      <bk-exception
        v-if="!componentList.length"
        class="exception-wrap-item exception-part"
        type="empty"
        scene="part"
      >
        {{ $t('暂无数据') }}
      </bk-exception>
      <bk-tab
        v-else
        :active.sync="tabActive"
        type="card"
        ext-cls="components-tab-cls"
        @tab-change="handleTabChange"
        :key="tabKey"
      >
        <bk-tab-panel
          v-for="(panel, index) in componentList"
          v-bind="panel"
          :key="index"
        >
          <div
            slot="label"
            class="tab-panel-wrapper"
          >
            <!-- icon -->
            <i
              class="paasng-icon paasng-check-circle-shape"
              v-if="panel.status === 'installed'"
            ></i>
            <i
              class="paasng-icon paasng-close-circle-shape"
              v-else-if="panel.status === 'installation_failed'"
            ></i>
            <i
              class="paasng-icon paasng-time-filled"
              v-else
            ></i>
            <span class="panel-name">{{ panel.name }}</span>
          </div>
        </bk-tab-panel>
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
        component_preferred_namespace: this.$t('命名空间'),
        component_image_registry: this.$t('镜像仓库'),
        app_address_type: this.$t('应用访问类型'),
        app_domains: this.$t('应用域名'),
      },
      componentDetail: {},
      pathMap: {
        subpath: this.$t('子路径'),
        subdomain: this.$t('子域名'),
      },
      firstLoad: false,
      tabKey: 0,
    };
  },
  created() {
    this.init();
  },
  computed: {
    curActiveTabData() {
      return this.componentList.find((v) => v.name === this.tabActive) ?? {};
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
    labelWidth() {
      return this.localLanguage === 'en' ? 150 : 120;
    },
  },
  watch: {
    data: {
      handler() {
        this.init();
      },
      deep: true,
    },
  },
  methods: {
    init() {
      this.isLoading = true;
      this.getClusterComponents();
    },
    handleTabChange(name) {
      this.firstLoad = true;
      this.getComponentDetail(name);
    },
    reset() {
      this.componentList = [];
      this.componentDetail = {};
      this.isLoading = false;
      this.cardLoading = false;
    },
    // 获取集群组件列表
    async getClusterComponents() {
      if (!this.data?.name) {
        this.reset();
        return;
      }
      try {
        const res = await this.$store.dispatch('tenant/getClusterComponents', { clusterName: this.data?.name });
        this.componentList = res.map((item) => {
          return {
            ...item,
            label: item.name,
          };
        });
        if (this.firstLoad) {
          this.handleTabChange(this.componentList[0]?.name);
        }
        this.tabKey += 1;
      } catch (e) {
        this.reset();
        this.catchErrorHandler(e);
      } finally {
        this.isLoading = false;
      }
    },
    // 获取集群组件详情
    async getComponentDetail(componentName) {
      if (!componentName) {
        this.reset();
        return;
      }
      this.cardLoading = true;
      try {
        const ret = await this.$store.dispatch('tenant/getComponentDetail', {
          clusterName: this.data?.name,
          componentName,
        });
        this.componentDetail = ret;
      } catch (e) {
        this.componentDetail = {};
        // 404 未安装
        if (e.status === 404) {
          return;
        }
        this.catchErrorHandler(e);
      } finally {
        this.isLoading = false;
        this.cardLoading = false;
      }
    },
    handleEdit(step) {
      this.$router.push({
        name: 'clusterCreateEdit',
        params: {
          type: 'edit',
        },
        query: {
          id: this.data.name,
          step,
          alone: true,
        },
      });
    },
  },
};
</script>

<style lang="scss" scoped>
.detail-components-container {
  position: relative;
  .tab-panel-wrapper {
    i {
      font-size: 14px;
      margin-right: 5px;
    }
    .paasng-check-circle-shape {
      color: #18c0a1;
    }
    .paasng-time-filled {
      color: #c4c6cc;
    }
    .paasng-close-circle-shape {
      color: #ea3636;
    }
  }
  .view-title {
    font-weight: 700;
    font-size: 14px;
    color: #313238;
    line-height: 22px;
    margin: 24px 0 12px 0;
    &:first-of-type {
      margin-top: 0;
    }
    &.comps-details {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding-top: 24px;
      border-top: 1px solid #dcdee5;
    }
    .bk-primary {
      font-weight: 400;
    }
  }
  .paasng-info-line {
    font-size: 14px;
    color: #979ba5;
  }
  .components-tab-cls {
    /deep/ .bk-tab-section {
      background: #f5f7fa;
      padding: 12px 16px 16px 16px !important;
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
