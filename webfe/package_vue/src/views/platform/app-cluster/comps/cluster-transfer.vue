<template>
  <div
    class="cluster-transfer"
    @click.stop
  >
    <!-- 集群穿梭框 -->
    <bk-transfer
      :source-list="sourceList"
      :target-list="targetList"
      :display-key="'name'"
      :setting-key="'name'"
      @change="handleChange"
      :show-overflow-tips="true"
      ext-cls="cluster-transfer-cls"
    >
      <div
        slot="left-header"
        class="left-header"
      >
        <label class="title">{{ '可选集群(' + this.sourceLength + ')' }}</label>
        <div class="add-all">
          <span
            :class="{ disabled: !this.sourceLength }"
            @click="addAll"
          >
            {{ $t('选择全部') }}
          </span>
        </div>
      </div>
      <div
        slot="right-header"
        class="right-header"
      >
        <label class="title">{{ '已选集群(' + this.targetLength + ')' }}</label>
        <div class="remove-all">
          <span
            :class="{ disabled: !this.targetLength }"
            @click="removeAll"
          >
            {{ $t('清空') }}
          </span>
        </div>
      </div>
      <div
        slot="target-option"
        slot-scope="data, index"
        class="transfer-source-item"
      >
        <div
          class="text"
          v-bk-overflow-tips="{ content: data.name, allowHTML: true }"
        >
          {{ data.name }}
        </div>
        <span class="default">{{ $t('默认') }}</span>
        <i class="bk-icon icon-close"></i>
      </div>
    </bk-transfer>
  </div>
</template>

<script>
export default {
  name: 'ClusterTransfer',
  props: {
    list: {
      type: Array,
      default: () => [],
    },
    defaultTargetList: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      sourceLength: 0,
      targetLength: 0,
      sourceList: this.list,
      targetList: [],
      targetValueList: [],
    };
  },
  created() {
    this.targetList.push(...this.defaultTargetList);
  },
  methods: {
    handleChange(sourceList, targetList, targetValueList) {
      this.sourceLength = sourceList.length;
      this.targetLength = targetList.length;
      this.targetValueList = targetValueList;
      this.$emit('change', targetValueList);
    },
    addAll() {
      if (!this.sourceLength) return;
      this.targetList = this.sourceList.map((item) => item.name);
    },
    removeAll() {
      if (!this.targetLength) return;
      this.targetList = [];
    },
    deselect(item) {
      const index = this.targetValueList.indexOf(item);
      this.targetValueList.splice(index, 1);
      this.targetList = this.targetValueList;
    },
  },
};
</script>

<style lang="scss" scoped>
.cluster-transfer-cls {
  /deep/ .slot-header {
    padding: 0 16px !important;
  }
  /deep/ .source-list,
  /deep/ .target-list {
    min-width: auto !important;
  }
  /deep/ .target-list {
    .content li:first-child .default {
      display: inline-block;
    }
    .content li:hover {
      .transfer-source-item {
        padding-right: 12px;
      }
      i {
        display: block;
      }
    }
  }
  .transfer-source-item {
    display: flex;
    align-items: center;
    overflow: hidden;
    .text {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      flex-shrink: 1;
      flex-grow: 1;
      /* 确保最小宽度为0，允许收缩 */
      min-width: 0;
    }
    .default {
      flex-shrink: 0;
      margin-left: 2px;
      display: none;
      height: 16px;
      line-height: 16px;
      padding: 0 4px;
      font-size: 10px;
      color: #ffffff;
      background: #ea3636;
      border-radius: 10px;
    }
    .icon-close {
      display: none;
      position: absolute;
      right: 10px;
      top: 50%;
      transform: translateY(-50%);
      color: #3a84ff;
    }
  }
}
.title {
  font-weight: 700;
  font-size: 14px;
  color: #4d4f56;
}
.add-all,
.remove-all {
  display: inline-block;
  float: right;
  cursor: pointer;
  font-size: 12px;
  span {
    color: #3a84ff;
    &.disabled {
      cursor: not-allowed;
      opacity: 0.5;
    }
  }
}
</style>
