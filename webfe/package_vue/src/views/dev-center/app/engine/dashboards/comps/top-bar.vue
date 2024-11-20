<template>
  <div class="dashboards-top-bar">
    <span class="title">{{ $t('仪表盘') }}</span>
    <bk-select
      :clearable="false"
      :disabled="false"
      :loading="loading"
      v-model="selectValue"
      style="width: 240px"
      ext-cls="dashboard-select-cls"
      ext-popover-cls="dashboard-select-popover"
      @change="handleChange"
    >
      <bk-option
        v-for="option in data"
        :key="option.name"
        :id="option.name"
        :name="option.display_name"
      ></bk-option>
      <div
        slot="extension"
        class="select-extension-cls"
        @click="viewMoreDashboards"
      >
        <i class="paasng-icon paasng-app-store"></i>
        {{ $t('查看更多仪表盘') }}
      </div>
    </bk-select>
  </div>
</template>

<script>
export default {
  name: 'DashboardsTopBar',
  props: {
    data: {
      type: Array,
      default: () => [],
    },
    loading: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      selectValue: '',
    };
  },
  watch: {
    data: {
      handler(list) {
        if (list.length) {
          const firstName = list[0].name;
          this.selectValue = firstName;
        }
      },
      deep: true,
    },
  },
  methods: {
    handleChange(name) {
      const curDashboardData = this.data.find((v) => v.name === name);
      this.$emit('change', curDashboardData);
    },
    viewMoreDashboards() {
      this.$emit('redirect');
    },
  },
};
</script>

<style lang="scss" scoped>
.dashboards-top-bar {
  display: flex;
  align-items: center;
  height: 52px;
  background: #fff;
  box-shadow: 0 3px 4px 0 #0000000a;
  font-size: 16px;
  color: #313238;
  padding: 0 24px;
  .title {
    margin-right: 24px;
  }
  .dashboard-select-cls:not(.is-focus) {
    background: #f0f1f5;
    border: none;
  }
}
.dashboard-select-popover {
  .select-extension-cls {
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    font-size: 12px;
    color: #4d4f56;
    i {
      font-size: 12px;
      margin-right: 5px;
      transform: translateY(0px);
    }
  }
}
</style>
