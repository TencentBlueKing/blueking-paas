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
        <div
          v-else
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
    </bk-exception>
  </div>
</template>

<script>
    import i18n from '@/language/i18n';
    export default {
        props: {
            keyword: {
                type: String,
                default: ''
            },
            // 是否为暂无数据
            empty: {
                type: Boolean,
                default: false
            },
            // 暂无数据
            emptyTitle: {
                type: String,
                default: i18n.t('暂无数据')
            },
            // 是否显示title
            isEmptyTitle: {
                type: Boolean,
                default: true
            },
            // 是否为异常
            abnormal: {
                type: Boolean,
                default: false
            },
            isContentText: {
                type: Boolean,
                default: true
            }
        },
        computed: {
            curType () {
                if (this.abnormal) {
                    return '500';
                } else if (!this.empty && this.keyword) {
                    return 'search-empty';
                } else {
                    return 'empty';
                }
            },
            curTitle () {
                if (this.abnormal) {
                    return this.$t('数据获取异常');
                } else if (!this.empty && this.keyword) {
                    return this.$t('搜索结果为空');
                } else {
                    return this.emptyTitle;
                }
            }
        },
        methods: {
            handlerClearFilter () {
                this.$emit('clear-filter');
            },
            toRefresh () {
                this.$emit('clear-filter');
                this.$emit('reacquire');
            }
        }
    };
</script>

<style lang="scss" scoped>
    .paas-table-serch {
        max-height: 280px;
        .search-empty-tips {
            font-size: 12px;
            color: #979BA5;
            .clear-search {
                cursor: pointer;
                color: #3a84ff;
            }
        }
        .empty-tips {
            color: #63656E;
        }
        .exception-part-title {
            color: #63656E;
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
