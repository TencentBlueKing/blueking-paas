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
        <span
          v-if="abnormal"
          class="refresh-tips"
          @click="toRefresh"
        >
          {{ $t('刷新') }}
        </span>
        <!-- 恒定条件不展示清空交互-->
        <template v-else>
          <div
            v-if="keyword !== '$CONSTANT'"
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
import i18n from '@/language/i18n';
export default {
  props: {
    keyword: {
      type: String,
      default: '',
    },
    // 是否为暂无数据
    empty: {
      type: Boolean,
      default: false,
    },
    // 暂无数据
    emptyTitle: {
      type: String,
      default: i18n.t('暂无数据'),
    },
    // 是否显示title
    isEmptyTitle: {
      type: Boolean,
      default: true,
    },
    // 是否为异常
    abnormal: {
      type: Boolean,
      default: false,
    },
    isContentText: {
      type: Boolean,
      default: true,
    },
    explanation: {
      type: String,
      default: '',
    },
  },
  computed: {
    curType() {
      if (this.abnormal) {
        return '500';
      } if (!this.empty && this.keyword) {
        return 'search-empty';
      }
      return 'empty';
    },
    curTitle() {
      if (this.abnormal) {
        return this.$t('数据获取异常');
      } if (!this.empty && this.keyword) {
        return this.$t('搜索结果为空');
      }
      return this.emptyTitle;
    },
  },
  methods: {
    handlerClearFilter() {
      this.$emit('clear-filter');
    },
    toRefresh() {
      this.$emit('clear-filter');
      this.$emit('reacquire');
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
