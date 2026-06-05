<template>
  <div class="paas-table-serch">
    <bk-exception
      class="exception-wrap-item exception-part"
      :type="curType"
      scene="part"
    >
      <div
        v-if="isEmptyTitle"
        class="exception-part-title"
      >
        {{ curTitle }}
        <p
          class="mt10"
          style="font-size: 12px; color: #979ba5"
          v-if="explanation"
        >
          {{ explanation }}
        </p>
      </div>
      <span v-else />
      <template v-if="curType !== 'empty' && isContentText">
        <!-- 异常状态：提供刷新入口 -->
        <span
          v-if="resolvedIsError"
          class="refresh-tips"
          @click="toRefresh"
        >
          {{ $t('刷新') }}
        </span>
        <!-- 搜索为空状态：提供清空筛选入口（恒定条件不展示） -->
        <template v-else>
          <div
            v-if="resolvedShowClear"
            class="search-empty-tips"
          >
            {{ $t('可以尝试 调整关键词 或') }}
            <span
              class="clear-search"
              @click="handlerClearFilter"
            >
              {{ $t('清空搜索条件') }}
            </span>
          </div>
        </template>
      </template>
    </bk-exception>
  </div>
</template>

<script>
// 表格空状态统一展示组件支持三种场景：
// 1. empty —— 数据为空（默认暂无数据）
// 2. search-empty —— 搜索/筛选后无结果
// 3. 接口请求异常

import i18n from '@/language/i18n';

export default {
  props: {
    // 是否强制展示暂无数据状态
    empty: {
      type: Boolean,
      default: false,
    },
    // 空状态展示的标题文案，默认 "暂无数据"
    emptyTitle: {
      type: String,
      default: i18n.t('暂无数据'),
    },
    // 是否显示 title 区域
    isEmptyTitle: {
      type: Boolean,
      default: true,
    },
    // 是否为接口异常状态
    isError: {
      type: Boolean,
      default: false,
    },
    // 搜索/筛选条件值，用于判断是否存在有效筛选条件
    condition: {
      type: [String, Number, Boolean, Object, Array],
      default: '',
    },
    // 是否显示「清空搜索条件」入口，undefined 时根据 condition 自动判断
    showClear: {
      type: Boolean,
      default: undefined,
    },
    // 是否显示操作引导区域（搜索提示 / 刷新按钮）
    isContentText: {
      type: Boolean,
      default: true,
    },
    // 附加说明文案，显示在 title 下方
    explanation: {
      type: String,
      default: '',
    },
  },

  computed: {
    // 接口异常标记
    resolvedIsError() {
      return this.isError;
    },

    // 是否存在有效的筛选条件
    resolvedHasCondition() {
      return this.hasActiveFilter(this.condition);
    },

    // 是否展示「清空搜索条件」交互
    resolvedShowClear() {
      if (typeof this.showClear === 'boolean') {
        return this.showClear;
      }
      return this.resolvedHasCondition;
    },

    // 当前 bk-exception 组件所需的 type 值
    curType() {
      if (this.resolvedIsError) {
        return '500';
      }
      if (this.empty) {
        return 'empty';
      }
      if (this.resolvedHasCondition) {
        return 'search-empty';
      }
      return 'empty';
    },

    // 当前展示的标题文案
    curTitle() {
      if (this.resolvedIsError) {
        return this.$t('数据获取异常');
      }
      if (this.empty) {
        return this.emptyTitle;
      }
      if (this.resolvedHasCondition) {
        return this.$t('搜索结果为空');
      }
      return this.emptyTitle;
    },
  },

  methods: {
    // 通知父组件清空筛选条件
    handlerClearFilter() {
      this.$emit('clear-filter');
    },

    toRefresh() {
      this.$emit('clear-filter');
      this.$emit('reacquire');
    },

    // 递归检测 value 中是否存在有效筛选值，支持 string、number、boolean、array、object 等类型
    hasActiveFilter(value) {
      if (Array.isArray(value)) {
        return value.some((item) => this.hasActiveFilter(item));
      }
      if (value && typeof value === 'object') {
        return Object.keys(value).some((key) => this.hasActiveFilter(value[key]));
      }
      if (typeof value === 'string') {
        return value.trim() !== '';
      }
      return Boolean(value);
    },
  },
};
</script>

<style lang="scss" scoped>
.paas-table-serch {
  max-height: 280px;
  .search-empty-tips {
    font-size: 12px;
    color: #979ba5;
    .clear-search {
      cursor: pointer;
      color: #3a84ff;
    }
  }
  .empty-tips {
    color: #63656e;
  }
  .exception-part-title {
    color: #63656e;
    font-size: 14px;
    margin-bottom: 12px;
  }
  .refresh-tips {
    cursor: pointer;
    color: #3a84ff;
  }
}
</style>
<style lang="scss">
.paas-table-serch .exception-wrap-item .bk-exception-img.part-img {
  height: 130px;
}
.bk-table-empty-block {
  height: 280px;
  max-height: 280px;
  display: flex;
  align-items: center;
  .bk-table-empty-text {
    padding: 0;
  }
}
</style>
