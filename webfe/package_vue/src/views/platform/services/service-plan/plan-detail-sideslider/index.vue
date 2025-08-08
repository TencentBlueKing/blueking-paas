<template>
  <bk-sideslider
    :is-show.sync="sidesliderVisible"
    :quick-close="true"
    show-mask
    width="960"
    @hidden="hidden"
    @shown="shown"
  >
    <div slot="header">
      <div class="header-box">
        <span>{{ $t('方案详情') }}</span>
        <span class="desc">{{ `${$t('方案')}：${data.name}` }}</span>
      </div>
    </div>
    <div
      class="sideslider-content"
      slot="content"
    >
      <bk-tab
        :active.sync="tabActive"
        type="card"
        ext-cls="plan-details-tab"
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
          <BaseInfo
            v-if="tabActive === 'planBaseInfo'"
            :data="displayInfoData"
            v-bind="$attrs"
            @operate="isRefresh = true"
            @change-details="changeDetails"
          />
          <ResourcePool
            v-else
            :data="data"
            :tenant-id="tenantId"
            @change="changeInstancesLength"
            @operate="isRefresh = true"
          />
        </div>
      </bk-tab>
    </div>
  </bk-sideslider>
</template>

<script>
import BaseInfo from './base-info.vue';
import ResourcePool from './resource-pool.vue';

export default {
  name: 'PlanDetailSideslider',
  components: {
    BaseInfo,
    ResourcePool,
  },
  props: {
    show: {
      type: Boolean,
      default: false,
    },
    data: {
      type: Object,
      default: () => ({}),
    },
    active: {
      type: String,
      default: '',
    },
    tenantId: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      tabActive: 'planBaseInfo',
      contentLoading: false,
      instancesLength: 0,
      isRefresh: false,
      displayInfoData: {},
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
    providerName() {
      return this.data.service_config?.provider_name;
    },
    panels() {
      const planList = [{ name: 'planBaseInfo', label: this.$t('基本信息') }];
      // provider_name 必须是 pool
      if (this.providerName === 'pool') {
        planList.push({ name: 'planResourcePool', label: `${this.$t('资源池')}（${this.instancesLength}）` });
      }
      return planList;
    },
  },
  methods: {
    hidden() {
      this.tabActive = 'planBaseInfo';
      if (this.isRefresh) {
        // 新建/编辑后，关闭侧栏需要刷新table
        this.$emit('refresh');
      }
      this.isRefresh = false;
    },
    shown() {
      this.instancesLength = this.data?.pre_created_instances?.length || 0;
      this.tabActive = this.active || 'planBaseInfo';
      this.displayInfoData = { ...this.data };
    },
    changeInstancesLength(length) {
      this.instancesLength = length;
    },
    // 方案详情
    changeDetails(details) {
      this.displayInfoData = {
        ...this.data,
        ...details,
      };
    },
  },
};
</script>

<style lang="scss" scoped>
.header-box {
  .desc {
    height: 22px;
    margin-left: 10px;
    padding-left: 8px;
    font-size: 14px;
    color: #979ba5;
    border-left: 1px solid #dcdee5;
  }
}
.sideslider-content {
  padding-top: 16px;
  background: #f5f7fa;
}
.plan-details-tab {
  /deep/ .bk-tab-header {
    height: 42px !important;
    background-image: none !important;
    padding-left: 40px;
    background: #f5f7fa;
    .bk-tab-label-list {
      border: none !important;
      .bk-tab-label-item {
        line-height: 42px !important;
        border: none;
        border-radius: 4px 4px 0 0;
        background: #eaebf0;
        margin-right: 8px;
      }
    }
  }
  /deep/ .bk-tab-section {
    border: none;
    background-color: #fff;
    padding: 16px 40px;
  }
}
</style>
