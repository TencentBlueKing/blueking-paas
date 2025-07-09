<template>
  <div class="cluster-details-container">
    <bk-resize-layout
      :immediate="true"
      :min="280"
      style="width: 100%"
    >
      <div
        class="list"
        slot="aside"
      >
        <!-- 收起详情 -->
        <div
          class="hide-icon"
          @click="$emit('toggle', false)"
        >
          <i class="paasng-icon paasng-angle-line-up"></i>
        </div>
        <div class="top-tool">
          <div class="left flex-row">
            <!-- <bk-button :theme="'primary'">
              <i class="paasng-icon paasng-plus"></i>
            </bk-button> -->
          </div>
          <bk-input
            class="search-input"
            v-model="searchValue"
            :placeholder="$t('搜索集群名称')"
            :right-icon="'bk-icon icon-search'"
            clearable
          ></bk-input>
        </div>
        <ul
          class="mt15 cluster-list"
          v-bkloading="{ isLoading: leftLoading, zIndex: 10 }"
        >
          <li class="header-item item">{{ $t('集群名称') }}</li>
          <li
            v-for="item in displayTenantList"
            :key="item.name"
            :class="['item', { active: activeName === item.name }]"
            @click="switchDetails(item.name)"
          >
            {{ item.name }}
            <i
              v-if="clustersStatus[item.name]?.hasIcon"
              class="paasng-icon paasng-unfinished"
              v-bk-tooltips="$t('集群配置未完成')"
            ></i>
          </li>
        </ul>
      </div>
      <div
        class="details-wrapper"
        slot="main"
      >
        <div
          class="close"
          @click="$emit('toggle', false)"
        >
          <bk-icon type="close" />
        </div>
        <bk-tab
          :active.sync="tabActive"
          type="card"
          ext-cls="cluster-details-tab"
          :key="`${activeName}-${Object.values(curClustersStatus).join('-')}`"
        >
          <bk-tab-panel
            v-for="(panel, index) in panels"
            v-bind="panel"
            :key="index"
          >
            <template slot="label">
              <span>{{ panel.label }}</span>
              <template
                v-if="panel.key !== 'node' && Object.keys(curClustersStatus)?.length && curClustersStatus?.hasIcon"
              >
                <i
                  v-if="!curClustersStatus?.[panel.key]"
                  class="paasng-icon paasng-unfinished"
                ></i>
              </template>
            </template>
          </bk-tab-panel>
          <div v-bkloading="{ isLoading: contentLoading, zIndex: 10 }">
            <!-- 详情 -->
            <keep-alive>
              <component
                :is="tabActive"
                :data="curDetailData"
                :cluster-name="activeName"
                :default-config="clusterDefaultConfigs"
              />
            </keep-alive>
          </div>
        </bk-tab>
      </div>
    </bk-resize-layout>
  </div>
</template>

<script>
import DetailInfo from './detail-info.vue';
import DetailComponents from './detail-components.vue';
import DetailFeature from './detail-feature.vue';
import DetailNodeInfo from './detail-node-info.vue';
import { mapState } from 'vuex';
export default {
  name: 'ClusterDetails',
  components: {
    DetailInfo,
    DetailComponents,
    DetailFeature,
    DetailNodeInfo,
  },
  data() {
    return {
      tabActive: 'DetailInfo',
      activeName: '',
      buttonList: [
        { name: 'cluster', icon: 'organization' },
        { name: 'tenant', icon: 'user2' },
      ],
      panels: [
        { name: 'DetailInfo', label: this.$t('集群信息'), key: 'basic' },
        { name: 'DetailComponents', label: this.$t('集群组件'), key: 'component' },
        { name: 'DetailFeature', label: this.$t('集群特性'), key: 'feature' },
        { name: 'DetailNodeInfo', label: this.$t('节点信息'), key: 'node' },
      ],
      searchValue: '',
      leftLoading: false,
      contentLoading: false,
      tenantList: [],
      curDetailData: {},
      clusterDefaultConfigs: {},
    };
  },
  computed: {
    ...mapState('tenant', {
      clustersStatus: (state) => state.clustersStatus,
      detailActiveName: (state) => state.detailActiveName,
      detailTabActive: (state) => state.detailTabActive,
    }),
    curClustersStatus() {
      return this.clustersStatus[this.activeName] ?? {};
    },
    // 字段模糊搜索
    displayTenantList() {
      const lowerCaseSearchTerm = this.searchValue.toLocaleLowerCase();
      if (!lowerCaseSearchTerm) {
        return this.tenantList;
      }
      // 过滤数据，检查 name 是否包含搜索词
      return this.tenantList.filter((item) => {
        return item.name?.toLocaleLowerCase().includes(lowerCaseSearchTerm);
      });
    },
  },
  created() {
    this.init();
  },
  beforeDestroy() {
    this.$store.commit('tenant/updatedDtailTabActive', 'DetailInfo');
  },
  methods: {
    init() {
      this.getClusterList();
      this.getClusterDefaultConfigs();
      this.tabActive = this.detailTabActive || 'DetailInfo';
    },
    switchDetails(name) {
      this.activeName = name || '';
      this.getClusterDetails();
    },
    // 获取集群列表
    async getClusterList() {
      this.leftLoading = true;
      this.contentLoading = true;
      try {
        const res = await this.$store.dispatch('tenant/getClusterList');
        this.tenantList = res;
        const { clusterId } = this.$route.params;
        if (clusterId) {
          this.switchDetails(clusterId);
        } else {
          this.switchDetails(this.detailActiveName || res[0]?.name);
        }
        setTimeout(() => {
          // 获取集群状态
          this.$emit('get-status', res);
        }, 200);
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.leftLoading = false;
      }
    },
    // 获取集群详情
    async getClusterDetails() {
      this.contentLoading = true;
      try {
        const ret = await this.$store.dispatch('tenant/getClusterDetails', {
          clusterName: this.activeName,
        });
        this.curDetailData = ret;
      } catch (e) {
        this.$nextTick(() => {
          this.curDetailData = {};
        });
        this.catchErrorHandler(e);
      } finally {
        this.contentLoading = false;
      }
    },
    // 获取集群默认配置项
    async getClusterDefaultConfigs() {
      try {
        const ret = await this.$store.dispatch('tenant/getClusterDefaultConfigs');
        this.clusterDefaultConfigs = ret;
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.cluster-details-container {
  min-height: 0;
  height: 100%;
  display: flex;
  margin-top: 16px;
  i.paasng-unfinished {
    margin-left: 5px;
    font-size: 14px;
    color: #f8b64f;
    transform: translateY(0);
  }
  /deep/ .clustertab-edit-btn-cls {
    position: absolute;
    right: 0;
    top: 0;
  }
  /deep/ .bk-resize-layout {
    gap: 16px;
    border: none;
    .bk-resize-layout-aside,
    .bk-resize-layout-main {
      border: none;
      background: #fff;
      box-shadow: 0 2px 4px 0 #1919290d;
      border-radius: 2px;
    }
    .bk-resize-layout-aside {
      min-width: 280px;
      .bk-resize-layout-aside-content {
        overflow: auto;
      }
    }
  }
  .cluster-details-tab {
    height: 100%;
    display: flex;
    flex-direction: column;
    /deep/ .bk-tab-section {
      height: 100%;
      min-height: 0;
      overflow: auto;
    }
  }
  .list {
    padding: 16px;
    .cluster-list {
      .item {
        position: relative;
        height: 42px;
        line-height: 42px;
        font-size: 12px;
        padding: 0 16px;
        margin-top: -1px;
        color: #3a84ff;
        background: #ffffff;
        border: 1px solid transparent;
        border-top-color: #dcdee5;
        &:hover {
          background-color: #f5f7fa;
        }
        &:last-child {
          border-bottom-color: #dcdee5;
        }
        &:not(.header-item) {
          cursor: pointer;
        }
        &.active {
          height: 42px;
          border: 1px solid #3a84ff;
          background: #f0f5ff;
          border-radius: 2px;
          z-index: 2;
          &::after {
            content: '';
            position: absolute;
            width: 0;
            height: 0;
            right: -8px;
            top: 50%;
            border: 4px solid transparent;
            border-left: 4px solid #3a84ff;
            transform: translateY(-50%);
          }
        }
      }
      .header-item {
        border-top-color: transparent;
        background: #fafbfd;
        color: #313238;
      }
    }
    .hide-icon {
      position: absolute;
      display: flex;
      align-items: center;
      right: -16px;
      top: 35%;
      width: 16px;
      height: 64px;
      color: #ffffff;
      background: #dcdee5;
      cursor: pointer;
      border-radius: 0 4px 4px 0;
      i {
        transform: rotate(90deg);
      }
    }
    .top-tool {
      display: flex;
      align-items: center;
      // gap: 8px;
      .switch-cls /deep/ .group-item {
        padding: 0 4px;
      }
      .bk-button {
        min-width: 0;
        padding: 0 10px;
      }
      .paasng-plus {
        font-size: 12px;
        font-weight: 700;
      }
      .search-input {
        flex: 1;
      }
    }
  }
  .details-wrapper {
    position: relative;
    height: 100%;
    // overflow: auto;
    .close {
      position: absolute;
      right: 7px;
      top: 4px;
      font-size: 28px;
      color: #979ba5;
      z-index: 9;
      i {
        cursor: pointer;
      }
    }
    /deep/ .bk-tab-header {
      height: 42px !important;
      background-image: none !important;
      background-color: #f0f1f5;
      .bk-tab-label-list {
        border: none !important;
        .bk-tab-label-item {
          line-height: 42px !important;
          position: relative;
          border: none;
          &::before,
          &:last-child::after {
            content: '';
            position: absolute;
            top: 50%;
            width: 1px;
            height: 16px;
            background: #c4c6cc;
            transform: translateY(-50%);
          }
          &::before {
            left: 0;
          }
          &:last-child::after {
            right: 0;
          }
          &.active {
            border-radius: 4px 4px 0 0;
          }
          &.active::before,
          &.active::after {
            background: transparent;
          }
          &.active + .bk-tab-label-item::before {
            background: transparent;
          }
          &.is-first::before {
            background: transparent !important;
          }
        }
      }
    }
    /deep/ .bk-tab-section {
      border: none;
      padding: 16px 24px;
    }
  }
}
</style>
