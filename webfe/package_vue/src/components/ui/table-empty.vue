<template>
  <div class="paas-table-serch">
    <template v-if="!empty && isEmpty === 'search' && keyword">
      <bk-exception
        class="exception-wrap-item exception-part"
        type="search-empty"
        scene="part"
      />
      <div class="search-empty-tips">
        {{ $t('可以尝试 调整关键词 或') }}
        <span
          class="clear-search"
          @click="handlerClearFilter"
        >{{ $t('清空搜索条件') }}</span>
      </div>
    </template>
    <template v-else>
      <bk-exception
        class="exception-wrap-item exception-part"
        type="empty"
        scene="part"
      >
        <span class="empty-tips">{{ $t('暂无数据') }}</span>
      </bk-exception>
    </template>
  </div>
</template>

<script>

    export default {
        props: {
            getDataCount: {
                type: Number,
                default: 0
            },
            keyword: {
                type: String,
                default: ''
            },
            data: {
                type: Array,
                default: () => []
            },
            // 是否为暂无数据
            empty: {
                type: Boolean,
                default: false
            }
        },
        computed: {
            isEmpty () {
                if (this.getDataCount <= 1 && !this.data.length) {
                    return 'empty';
                }
                return 'search';
            }
        },
        methods: {
            handlerClearFilter () {
                this.$emit('clear-filter');
            }
        }
    };
</script>

<style lang="scss" scoped>
    .paas-table-serch {
        max-height: 280px;
        .search-empty-tips {
            margin-top: 8px;
            color: #979BA5;
            .clear-search {
                cursor: pointer;
                color: #3a84ff;
            }
        }
        .empty-tips {
            color: #63656E;
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
