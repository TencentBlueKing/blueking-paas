<template>
  <div class="mr20 global-search-modal">
    <!-- 查看态 -->
    <div
      ref="outFocusRef"
      class="out-focus-tool"
      @click="handleSearchFocus"
    >
      <span>{{ filterKey ? filterKey : $t('搜索') }}</span>
      <i
        class="input-right-icon bk-icon bk-icon icon-search"
        @click="handleEnter"
      />
    </div>
    <!-- focus -->
    <div
      v-show="isFocus"
      class="global-search-focus"
      :style="{ left: leftPosition + 'px' }"
    >
      <div
        :class="['ps-search', 'clearfix', { focus: isFocus }]"
        v-bk-clickoutside="handleClickOutSide"
      >
        <input
          ref="searchInputRef"
          v-model="filterKey"
          type="text"
          :placeholder="$t('搜索')"
          @keypress.enter="handleEnter"
          @focus="handleFocus"
        />
        <i
          v-if="filterKey && isFocus"
          class="bk-icon icon-close-circle-shape clear-icon"
          @click="clearInputValue"
        />
        <i
          class="input-right-icon bk-icon bk-icon icon-search"
          @click="handleEnter"
        />
      </div>
      <div class="search-result-content">
        <search-result
          ref="searchRef"
          :search-history="searchHistory"
          :search-value="filterKey"
          @close-search-mode="handleSearchClose"
          @load-history="loadSearchHistory"
          @change="handleChange"
        />
      </div>
    </div>
  </div>
</template>

<script>
import searchResult from './search-result.vue';
import { parentClsContains } from '@/common/tools';

const SEARCHWIDTH = 720; // 固定元素的宽度

export default {
  name: 'GlobalSearch',
  components: {
    searchResult,
  },
  data() {
    return {
      isFocus: false,
      leftPosition: 0,
      filterKey: '',
      searchHistory: [],
      toolEl: null,
    };
  },
  mounted() {
    this.toolEl = this.$refs.outFocusRef;
    window.addEventListener('resize', this.updateFixedElementPosition);
  },
  beforeDestroy() {
    window.removeEventListener('resize', this.updateFixedElementPosition);
  },
  methods: {
    // 更新 focus 状态下全局搜索框的位置
    updateFixedElementPosition() {
      const toolRect = this.toolEl.getBoundingClientRect();
      this.leftPosition = toolRect.right - SEARCHWIDTH;
    },
    // 点击默认显示的输入框
    handleSearchFocus() {
      this.toolEl = this.$refs.outFocusRef;
      this.updateFixedElementPosition();
      this.isFocus = true;
      this.$nextTick(() => {
        this.$refs.searchInputRef.focus();
        this.$refs.searchInputRef.click();
      });
    },
    // enter键 选择事件回调
    handleEnter() {
      if (!this.filterKey) {
        this.$refs.searchRef.clearData();
      }
      if (this.filterKey !== '') {
        this.saveSearchHistory(this.filterKey);
        this.$refs.searchRef.handleSearch();
      }
    },
    handleClickOutSide(e) {
      const result = parentClsContains('search-result-content', e.target);
      if (!result) {
        this.isFocus = false;
      }
    },
    // 聚焦事件
    handleFocus() {
      this.loadSearchHistory();
      this.isFocus = true;
    },
    handleSearchClose() {
      this.isFocus = false;
    },
    handleChange(text) {
      this.filterKey = text;
    },
    // 清空搜索框
    clearInputValue() {
      this.filterKey = '';
      this.$refs.searchRef.clearData();
    },
    // 加载搜索历史
    loadSearchHistory() {
      const history = localStorage.getItem('searchHistory');
      if (history) {
        this.searchHistory = JSON.parse(history);
      }
    },
    // 存储搜索历史
    saveSearchHistory(query) {
      this.searchHistory = [query, ...this.searchHistory.filter(item => item !== query)];
      localStorage.setItem('searchHistory', JSON.stringify(this.searchHistory));
    },
  },
};
</script>

<style lang="scss" scoped>
@mixin search-input-styles {
  cursor: text;
  height: 32px;
  padding: 0 48px 0 14px;
  line-height: 30px;
  background: none;
  float: left;
  color: #d3d9e4;
  border: none;
  z-index: 1;
  border-radius: 2px;
  font-size: 12px;
}
.global-search-modal {
  .global-search-focus {
    position: fixed;
    top: calc(var(--app-notice-height) + 9px);
    right: 0;
    z-index: 999;
  }
  .out-focus-tool {
    @include search-input-styles;
    display: flex;
    align-items: center;
    position: relative;
    width: 240px;
    background: #252f43;
    color: #979ba5;

    .icon-search {
      position: absolute;
      right: 12px;
      top: 9px;
      font-size: 14px;
      cursor: pointer;
    }
  }
  .header-search-result,
  .search-result-content {
    width: 720px;
    height: 440px;
    margin-top: 5px;
    background: #ffffff;
    border: 1px solid #dcdee5;
    box-shadow: 0 2px 6px 0 #0000001a;
    border-radius: 2px;
    transition: all 0.1s;
    overflow-y: auto;

    .search-result-panel {
      box-shadow: 0px 1px 5px #e5e5e5;
      border: 1px solid #eee;
      border-radius: 2px;
    }

    h3 {
      padding: 10px 15px;
    }

    .paas-search-trigger {
      position: relative;
      top: 5px;
      width: calc(100% - 10px);
      margin: 0 auto;
      line-height: 24px;
      border-radius: 2px;
      background: #f0f1f5;
      font-size: 12px;
      color: #979ba5;
      text-align: center;
      cursor: pointer;
      &:hover {
        color: #3a84ff;
      }
    }
  }

  .search-result-content {
    position: absolute;
    top: 35px;
    left: 0;
    z-index: 999;
  }
}
.ps-search {
  background: #303d55;
  overflow: hidden;
  border-radius: 2px;
  position: relative;
  width: 720px;

  &.focus {
    input[type='text'] {
      outline: none;
      width: 720px;
      background: #394561 !important;
      color: #fff;
    }
  }

  input[type='text'] {
    @include search-input-styles;
    width: 720px;

    &:focus {
      outline: none;
      background: #394561;
    }
  }

  .clear-icon,
  .icon-search {
    position: absolute;
    cursor: pointer;
    color: #c4c6cc;
    top: 9px;
  }
  i.clear-icon {
    right: 30px;
    font-size: 14px;
    &:hover {
      color: #979ba5;
    }
  }
  i.icon-search {
    right: 12px;
    &:hover {
      color: #3a84ff;
    }
  }
}
</style>
