<template>
  <div class="paas-empty-dark">
    <template v-if="abnormal || !keyword">
      <!-- 异常 -->
      <img
        v-if="abnormal"
        :src="abnormalSvg"
      />
      <img
        v-else
        :src="emptyDarkImg"
      />
      <p class="empty-tips">
        {{ emptyTitle }}
      </p>
      <span
        v-if="abnormal"
        class="refresh"
        @click="toRefresh"
      >
        {{ $t('刷新') }}
      </span>
    </template>
    <template v-else>
      <img :src="searchEmptyImg" />
      <div class="empty-tips">
        <p>{{ $t('搜索结果为空') }}</p>
        <div class="search-empty-tips">
          {{ $t('可以尝试 调整关键词 或') }}
          <span
            class="clear-search"
            @click="handlerClearFilter"
          >
            {{ $t('清空搜索条件') }}
          </span>
        </div>
      </div>
    </template>
  </div>
</template>

<script>
import i18n from '@/language/i18n';
import abnormalSvg from '@/../static/images/abnormal.svg';
import emptyDarkImg from '@/../static/images/empty-dark.png';
import searchEmptyImg from '@/../static/images/search-empty.png';

export default {
  data() {
    return {
      abnormalSvg,
      emptyDarkImg,
      searchEmptyImg,
    };
  },
  props: {
    keyword: {
      type: String,
      default: '',
    },
    // 暂无数据
    emptyTitle: {
      type: String,
      default: i18n.t('暂无数据'),
    },
    // 是否为异常
    abnormal: {
      type: Boolean,
      default: false,
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
.paas-empty-dark {
  text-align: center;
  .empty-tips {
    font-size: 14px;
    color: #979ba5;
    margin-bottom: 10px;
  }
  .search-empty-tips {
    font-size: 12px;
    .clear-search {
      color: #699df4;
      cursor: pointer;
    }
  }
  .refresh {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
}
</style>
