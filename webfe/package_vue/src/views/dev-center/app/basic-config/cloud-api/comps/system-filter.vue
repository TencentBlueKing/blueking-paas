<template lang="html">
  <div
    ref="filterRef"
    class="paasng-api-sys-filter"
  >
    <div style="height: 100%">
      <section style="padding: 0 10px">
        <label class="title">
          {{ isGateway ? $t('网关列表') : $t('系统列表') }}
          <span class="fr mt2 paasng-badge">{{ curList.length }}</span>
        </label>
        <bk-input
          v-model="searchValue"
          :placeholder="isGateway ? $t('请输入网关名称、描述') : $t('请输入系统名称、描述')"
          clearable
          right-icon="bk-icon icon-search"
          @input="handleSearch"
        />
      </section>
      <div class="system-list">
        <template v-if="curList.length > 0">
          <div
            v-for="(item, index) in curList"
            :key="index"
            :class="['item', { active: curSelect === item.id }]"
            @click="handleSelectSys(item)"
          >
            <p
              v-bk-overflow-tips
              class="name"
            >
              <span v-dompurify-html="highlight(item)" />
              <PaasTag
                v-if="!isGateway && item.tag !== ''"
                size="small"
                :class="[
                  { inner: [$t('内部版'), $t('互娱外部版')].includes(item.tag) },
                  { clound: [$t('上云版'), $t('互娱外部上云版')].includes(item.tag) },
                ]"
              >
                {{ item.tag }}
              </PaasTag>
              <PaasTag
                v-if="isGateway && item.tenant_mode === 'global'"
                theme="warning"
                size="small"
              >
                {{ $t('全租户') }}
              </PaasTag>
            </p>
            <p
              v-bk-overflow-tips
              class="desc"
              v-dompurify-html="highlightDesc(item)"
            />
          </div>
        </template>
        <template v-else>
          <div class="empty-wrapper">
            <table-empty
              :keyword="tableEmptyConf.keyword"
              @clear-filter="clearFilter"
            />
          </div>
        </template>
      </div>
    </div>
  </div>
</template>
<script>
import PaasTag from '@/components/paas-tag';

export default {
  components: {
    PaasTag,
  },
  props: {
    list: {
      type: Array,
      default: () => [],
    },
    type: {
      type: String,
      default: 'gateway',
    },
  },
  data() {
    return {
      curList: [],
      searchValue: '',
      isScrollFixed: false,
      summaryOffsetLeft: 10,
      style: {
        position: 'fixed',
        top: `40px`,
        'z-index': 100,
        padding: '10px',
        width: '240px',
        background: '#fff',
        'box-shadow': '0 2px 6px 0 rgba(0, 0, 0, .2)',
        'min-height': 'calc(100vh - 175px)',
      },
      curSelect: '',
      tableEmptyConf: {
        keyword: '',
      },
    };
  },
  computed: {
    isGateway() {
      return this.type === 'gateway';
    },
  },
  watch: {
    list: {
      handler(value) {
        this.curList = [...value];
        if (this.curList.length > 0) {
          this.curSelect = this.curList[0].id;
        }
        this.querySelect();
      },
      immediate: true,
    },
    searchValue(newVal, oldVal) {
      if (newVal === '' && oldVal !== '' && this.isFilter) {
        this.isFilter = false;
        this.curList = [...this.list];
      }
    },
  },
  mounted() {
    window.addEventListener('scroll', this.handleScroll);

    window.addEventListener('resize', this.handleResize);

    this.$once('hook:beforeDestroy', () => {
      window.removeEventListener('scroll', this.handleScroll);
      window.removeEventListener('resize', this.handleResize);
    });
  },
  methods: {
    handleSearch(payload) {
      if (payload === '') {
        return;
      }
      this.isFilter = true;
      this.curList = this.list.filter((item) => {
        const regex = new RegExp('(' + payload + ')', 'gi');
        return (item.name && !!item.name.match(regex)) || (item.description && !!item.description.match(regex));
      });
      this.updateTableEmptyConfig();
    },

    // 根据query参数选择对应网关
    querySelect() {
      const query = this.$route.query;
      if (!Object.keys(query).length) {
        return;
      }
      this.searchValue = query.apiName;
      this.handleSearch(this.searchValue);
      if (this.curList.length) {
        this.handleSelectSys(this.curList[0]);
        this.$emit('on-refresh', true);
      }
    },

    handleResize() {
      this.computedBoxFixed();
      this.style['left'] = `${this.summaryOffsetLeft - 10}px`;
    },

    handleSelectSys(payload) {
      this.curSelect = payload.id;
      this.$emit('on-select', payload);
      this.$emit('on-refresh', false);
    },

    handleScroll() {
      const box = this.$refs.filterRef;
      if (box && box.getBoundingClientRect) {
        const top = box.getBoundingClientRect().top;
        if (top <= 40) {
          this.isScrollFixed = true;
          this.computedBoxFixed();
          this.style['left'] = `${this.summaryOffsetLeft - 10}px`;
        } else {
          this.isScrollFixed = false;
          this.isResize = false;
        }
      }
    },

    computedBoxFixed() {
      const box = this.$refs.filterRef;
      if (box && box.getBoundingClientRect) {
        const elementRect = box.getBoundingClientRect();
        this.summaryOffsetLeft = elementRect.x;
      }
    },

    highlight(item) {
      if (!item || !item.name) {
        return '--';
      }
      const regex = new RegExp('(' + this.searchValue + ')', 'gi');
      return item.name.replace(regex, '<filtermark>$1</filtermark>');
    },

    highlightDesc(item) {
      if (!item || !item.description) {
        return this.$t('暂无描述');
      }
      if (item.description !== '' || item.description !== null) {
        const regex = new RegExp('(' + this.searchValue + ')', 'gi');
        return item.description.replace(regex, '<filtermark>$1</filtermark>');
      }
      return this.$t('暂无描述');
    },

    clearFilter() {
      this.searchValue = '';
    },

    updateTableEmptyConfig() {
      this.tableEmptyConf.keyword = this.searchValue;
    },
  },
};
</script>
<style lang="scss" scoped>
.paasng-api-sys-filter {
  height: 100%;
  color: #63656e;
  .mt2 {
    margin-top: 2px;
  }
  .title {
    display: block;
    margin-bottom: 8px;
  }
  .paasng-badge {
    min-width: 30px;
    height: 18px;
    background: #f0f1f5;
    border-radius: 2px;
    font-size: 12px;
    text-align: left;
    color: #979ba5;
    display: inline-block;
    line-height: 18px;
    text-align: center;
    padding: 0 5px;
  }
  .system-list {
    position: relative;
    margin-top: 10px;
    height: 560px;
    overflow-y: auto;
    .item {
      position: relative;
      padding: 0 10px;
      height: 52px;
      text-align: left;
      overflow: hidden;
      cursor: pointer;
      &:hover {
        background: #f0f1f5;
      }
      &.active {
        background: #e1ecff;
        .name {
          color: #3a84ff;
        }
      }
      .name {
        max-width: 217px;
        font-size: 14px;
        text-align: left;
        color: #63656e;
        line-height: 18px;
        margin: 2px 0;
        overflow: hidden;
        white-space: nowrap;
        text-overflow: ellipsis;
      }
      .desc {
        max-width: 217px;
        font-size: 12px;
        text-align: left;
        color: #979ba5;
        line-height: 18px;
        overflow: hidden;
        white-space: nowrap;
        text-overflow: ellipsis;
      }
      .paas-default-tag {
        position: relative;
        top: -1px;
        margin-left: 5px;
        font-size: 12px;
      }
      .inner {
        color: rgb(58, 171, 255);
        opacity: 0.7;
      }
      .clound {
        color: #45e35f;
      }
    }
    .empty-wrapper {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      overflow: hidden;
      width: 100%;
      i {
        font-size: 36px;
        color: #c3cdd7;
      }
    }
  }
}
</style>
<style>
filtermark {
  font-weight: 700;
  color: #3a84ff;
  font-style: normal;
}
</style>
