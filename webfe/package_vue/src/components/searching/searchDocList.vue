<template>
  <ul :class="theme">
    <template v-if="isLoading">
      <li>
        <img
          class="loading"
          src="/static/images/btn_loading.gif"
        ><span> {{ $t('搜索中...') }} </span>
      </li>
    </template>
    <template v-else>
      <li
        v-if="docList.length === 0"
        class="no-data"
      >
        <span> {{ $t('无相关文档') }} </span>
      </li>
      <li
        v-for="(item, index) in docList"
        v-if="!max || index < max"
        :key="index"
        :class="{ 'on': curActiveIndex === index }"
      >
        <a
          :href="`${item.url}`"
          target="_blank"
        >{{ item.title }}
        </a>
      </li>
    </template>
  </ul>
</template>

<script>
    import selectEventMixin from '@/components/searching/selectEventMixin';
    import _ from 'lodash';

    export default {
        mixins: [selectEventMixin],
        props: {
            theme: {
                type: String
            },
            filterKey: {
                type: String
            },
            max: {
                type: Number
            }
        },
        data: function () {
            return {
                isLoading: false,
                docList: []
            };
        },
        watch: {
            filterKey () {
                this.curActiveIndex = -1;
                this.fetchObj();
            }
        },
        created () {
            this.init();
        },
        methods: {
            getSelectListLength: function () {
                return this.docList.length;
            },
            init: function () {
                this.fetchObj();
            },
            enterSelect: function () {
                window.open(this.docList[this.curActiveIndex].url);
            },
            fetchObj: _.debounce(function () {
                this.isLoading = true;
                this.filterKey && this.$store.dispatch('search/fetchSearchDoc', this.filterKey).then(
                    docList => {
                        this.docList = this.max ? docList.splice(0, this.max) : docList;
                    }
                ).finally(
                    res => {
                        this.isLoading = false;
                    }
                );
            }, 350)
        }
    };
</script>

<style lang="scss" scoped>
    @import "../../assets/css/components/conf.scss";

    ul {
        background: #fff;
        max-height: 500px;
        overflow: auto;

        li {
            line-height: 32px;
            padding: 0 20px;

            a {
                color: $appMainFontColor;
                font-size: 14px;
                display: block;
                overflow: hidden;
                white-space: nowrap;
                text-overflow: ellipsis;
            }

            &:hover,
            &.on {
                background: #F0F1F5;

                a {
                    color: $appPrimaryColor;
                }
            }

            &.no-data:hover {
                background: #FFF;
            }
        }

        .loading {
            margin-right: 5px;
            vertical-align: middle;
        }
    }
</style>
