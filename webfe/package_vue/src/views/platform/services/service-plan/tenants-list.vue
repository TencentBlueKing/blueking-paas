<template>
  <div
    class="tenants-list-container"
    v-bkloading="{ isLoading: loading, zIndex: 10 }"
  >
    <div class="search">
      <bk-input
        :clearable="true"
        v-model="searchValue"
        :right-icon="'bk-icon icon-search'"
        :placeholder="$t('搜索租户')"
      ></bk-input>
    </div>
    <ul class="list">
      <li
        v-for="item in tenants"
        :key="item.id"
        :class="['item', { actvie: actvieId === item.id }]"
        @click="switchTenant(item)"
      >
        {{ item.name }}
      </li>
    </ul>
  </div>
</template>

<script>
export default {
  name: 'TenantsList',
  props: {
    tenants: {
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
      searchValue: '',
      actvieId: '',
    };
  },
  watch: {
    tenants(newVal) {
      this.actvieId = newVal[0] && newVal[0]?.id;
    },
  },
  methods: {
    switchTenant(row) {
      if (this.actvieId === row.id) return;
      this.actvieId = row.id;
      this.$emit('change', row.id);
    },
  },
};
</script>

<style lang="scss" scoped>
.tenants-list-container {
  flex-shrink: 0;
  width: 240px;
  .search {
    padding: 16px;
    padding-bottom: 0;
  }
  .list {
    margin-top: 12px;
    .item {
      line-height: 32px;
      height: 32px;
      padding: 0 8px;
      font-size: 12px;
      color: #4d4f56;
      cursor: pointer;
      &.actvie {
        background: #e1ecff;
        color: #3a84ff;
      }
    }
  }
}
</style>
