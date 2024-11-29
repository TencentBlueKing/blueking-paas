<template>
  <section :class="['plugin-filter-module', { en: localLanguage === 'en' }]">
    <bk-select
      v-model="curSortValue"
      :clearable="false"
      ext-cls="filters-select-cls"
      ext-popover-cls="filters-select-popover-cls"
      @change="handleChange"
    >
      <bk-option
        v-for="item in optionList"
        :id="item.value"
        :name="item.text"
        :key="item.value"
      ></bk-option>
    </bk-select>
    <div
      :class="['filter-right-icon', { active: filterActive }]"
      v-bk-tooltips="{ content: filterTips }"
      @click.stop="switchOrder"
    >
      <i :class="['paasng-icon', orderBy.startsWith('-') ? 'paasng-shengxu' : 'paasng-jiangxu']" />
    </div>
  </section>
</template>

<script>
const FILTER_TIP = {
  id: 'A - Z',
  '-id': 'Z - A',
  created: '最早',
  '-created': '最新',
  updated: '最早',
  '-updated': '最新',
};
export default {
  data() {
    return {
      curSortValue: '-updated',
      optionList: [
        { text: this.$t('插件 ID'), value: 'id' },
        { text: this.$t('创建时间'), value: '-created' },
        { text: this.$t('操作时间'), value: '-updated' },
      ],
      orderBy: '-updated',
    };
  },
  computed: {
    localLanguage() {
      return this.$store.state.localLanguage;
    },
    filterActive() {
      return this.orderBy.includes('id') ? this.orderBy.startsWith('-') : !this.orderBy.startsWith('-');
    },
    filterTips() {
      return FILTER_TIP[this.orderBy];
    },
  },
  methods: {
    // 过滤条件变化
    handleChange(id) {
      this.curSortValue = id;
      this.orderBy = id;
      this.$emit('change', this.curSortValue);
    },
    // 切换排序规则
    switchOrder() {
      this.orderBy = this.orderBy.startsWith('-') ? this.orderBy.replace('-', '') : `-${this.orderBy}`;
      this.$emit('change', this.orderBy);
    },
  },
};
</script>

<style lang="scss" scoped>
.plugin-filter-module {
  display: flex;
  margin: 3px 16px 0;
  width: 117px;
  height: 32px;
  background: #eaebf0;
  border-radius: 2px;
  &.en {
    width: 145px;
  }
  /deep/ .bk-tooltip-ref {
    display: block;
  }
  .bk-tooltip {
    flex: 1;
    white-space: nowrap;
    display: block;
    .tippy-active {
      background: #ffffff;
      border: 1px solid #3a84ff;
      border-radius: 2px 0 0 2px;
    }
  }
  .text {
    position: relative;
    padding: 0 8px;
    font-size: 12px;
    color: #63656e;
    flex: 1;
    line-height: 32px;
    cursor: pointer;
    text-overflow: ellipsis;
    white-space: nowrap;
    overflow: hidden;
    &:hover {
      background: #dcdee5;
      border-radius: 2px 0 0 2px;
    }
  }
  .filter-right-icon {
    flex-shrink: 0;
    position: relative;
    cursor: pointer;
    width: 30px;
    display: flex;
    align-items: center;
    justify-content: center;

    &::before {
      content: '';
      position: absolute;
      left: 0;
      top: 50%;
      transform: translateY(-50%);
      height: 14px;
      width: 1px;
      background-color: #dcdee5;
    }

    i {
      color: #979ba5;
    }

    &:hover {
      background: #dcdee5;
      border-radius: 0 2px 2px 0;
    }
    &.active {
      i {
        color: #3a84ff;
      }
    }
  }
}
.filters-select-cls {
  min-width: 0;
  flex: 1;
  border: none;
  /deep/ .bk-select-name {
    padding: 0 10px;
  }
  /deep/ .bk-select-angle {
    display: none;
  }
  /deep/ .bk-tooltip-ref.tippy-active {
    background: #ffffff;
    border: 1px solid #3a84ff;
    border-radius: 2px 0 0 2px;
  }
}
.filters-select-popover-cls .bk-options-wrapper .bk-options {
  .bk-option.is-selected {
    background: #e1ecff !important;
  }
  .bk-option:hover {
    color: #63656e;
    background: #f5f7fa;
  }
}
</style>
