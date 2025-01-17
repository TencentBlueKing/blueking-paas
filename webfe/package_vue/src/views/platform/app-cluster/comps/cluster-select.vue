<template>
  <div :class="{ 'has-label': hasLabel }">
    <div class="label-box">{{ label }}</div>
    <bk-select
      :disabled="false"
      v-model="selectValue"
      :scroll-height="300"
      multiple
      display-tag
      ext-cls="cluster-select-cls"
      ext-popover-cls="cluster-select-popover-cls"
    >
      <div
        slot="trigger"
        class="cluster-wrapper"
      >
        <template v-if="selectValue.length">
          <div
            v-for="item in selectValue"
            class="tag"
            :key="item"
            @click.stop
          >
            {{ item }}
            <i
              class="bk-icon icon-close"
              @click.stop="handleDeselect(item)"
            ></i>
          </div>
          <i class="bk-select-angle bk-icon icon-angle-down"></i>
        </template>
        <div
          class="placeholder"
          v-else
        >
          {{ $t('使用默认集群') }}
          <i class="bk-select-angle bk-icon icon-angle-down"></i>
        </div>
      </div>
      <bk-option
        :id="'cluster'"
        :name="'cluster'"
      >
        <ClusterTransfer
          ref="clusterTransfer"
          :list="availableClusters"
          :default-target-list="editData"
          @change="transferChange"
        />
      </bk-option>
    </bk-select>
  </div>
</template>

<script>
import ClusterTransfer from './cluster-transfer.vue';
export default {
  props: {
    hasLabel: {
      type: Boolean,
      default: false,
    },
    label: {
      type: String,
      default: '',
    },
    env: {
      type: String,
      default: '',
    },
    editData: {
      type: Array,
      default: () => [],
    },
  },
  components: {
    ClusterTransfer,
  },
  data() {
    return {
      selectValue: [],
    };
  },
  computed: {
    availableClusters() {
      return this.$store.state.tenant.availableClusters;
    },
    curTenantData() {
      return this.$store.state.tenant.curTenantData;
    },
  },
  watch: {
    selectValue: {
      handler(newValue) {
        if (this.env) {
          this.$emit('change', {
            [this.env]: newValue,
          });
          return;
        }
        this.$emit('change', newValue);
      },
      deep: true,
    },
  },
  methods: {
    // 穿梭框change
    transferChange(data) {
      this.selectValue = data;
    },
    // 取消选择当前的tag
    handleDeselect(data) {
      this.$refs.clusterTransfer?.deselect(data);
    },
  },
};
</script>

<style lang="scss" scoped>
.has-label {
  display: flex;
  .label-box {
    display: flex;
    align-items: center;
    flex-shrink: 0;
    min-width: 78px;
    height: auto;
    padding: 0 8px;
    font-size: 12px;
    color: #4d4f56;
    background: #fafbfd;
    border: 1px solid #c4c6cc;
    border-right: none;
    border-radius: 2px 0 0 2px;
  }
  .cluster-select-cls {
    border-radius: 0 2px 2px 0;
  }
}
.cluster-select-cls {
  min-height: 32px;
  height: auto;
  flex: 1;
}
.cluster-wrapper {
  min-height: 30px;
  padding: 0 30px 0 10px;
}
.placeholder {
  font-size: 12px;
  color: #c4c6cc;
}
.tag {
  display: inline-flex;
  align-items: center;
  height: 22px;
  line-height: 22px;
  padding: 0 2px 0 5px;
  background: #f0f1f5;
  border-radius: 2px;
  margin-right: 4px;
  .icon-close {
    margin-left: 5px;
    font-size: 18px;
    color: #979ba5;
    &:hover {
      color: #63656e;
    }
  }
  &:hover {
    background-color: #dcdee5;
  }
}
</style>
<style lang="scss">
.cluster-select-popover-cls {
  .bk-option:hover {
    color: #63656e;
    background-color: #fff !important;
  }
  .bk-option .bk-option-content {
    padding: 0 6px !important;
  }
}
</style>
