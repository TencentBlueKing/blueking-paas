<template>
  <ul
    :class="theme"
    class="ps-app-list"
  >
    <template v-if="isLoading">
      <li>
        <img
          class="loading"
          src="/static/images/btn_loading.gif"
        >
        <span> {{ $t('搜索中...') }} </span>
      </li>
    </template>
    <template v-else>
      <li
        v-if="appList.length === 0"
        class="no-data"
      >
        <span> {{ $t('无应用') }} </span>
      </li>
      <!-- 在顶部导航是需要控制显示应用的个数 -->
      <li
        v-for="(item, index) in appList"
        :key="index"
        :class="{ 'on': curActiveIndex === index }"
      >
        <a
          href="javascript:void(0);"
          @click="handlerSelectApp(item)"
        >
          <span class="app-name">{{ item.name }}</span>
          <span class="app-code">{{ item.code }}</span>
        </a>
      </li>
    </template>
  </ul>
</template>

<script>
    import _ from 'lodash';
    import selectEventMixin from '@/components/searching/selectEventMixin';

    export default {
        mixins: [selectEventMixin],
        props: {
            theme: {
                type: [Object, String]
            },
            filterKey: {
                type: String
            },
            max: {
                type: Number
            },
            searchAppsRouterName: {
                type: String
            },
            params: {
                type: Object
            }
        },
        data: function () {
            return {
                isLoading: false,
                appList: []
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
            // 拼接当前页新路由地址
            getTarget (appCode, moduleId) {
                const target = {
                    name: '',
                    params: {
                        ...this.$route.params,
                        id: appCode,
                        moduleId: moduleId
                    },
                    query: {
                        ...this.$route.query
                    }
                };
                target['name'] = (this.searchAppsRouterName === 'customed' ? this.$route.name : 'appSummary');
                if (['monitorAlarm', 'appLog'].includes(this.$route.name)) {
                    target['query'] = {};
                }

                return target;
            },
            init () {
                this.fetchObj();
            },
            getSelectListLength () {
                return this.appList.length;
            },
            handlerSelectApp (app) {
                const params = this.getTarget(app.code, app.moduleId);
                console.log('app-quick-search', params);
                // 更新nav
                this.$store.commit('updateNavType', app);
                // 刷新左侧导航(applogo\appname\appcode)
                this.$emit('selectAppCallback');
                this.$router.push(params);
            },
            enterSelect () {
                if (this.appList.length === 0 || this.curActiveIndex < 0) {
                    return;
                }
                const app = this.appList[this.curActiveIndex];
                // 切换应用后的操作
                this.handlerSelectApp(app);
            },
            handleFetch (res) {
                return this.max ? res.splice(0, this.max) : res;
            },
            fetchObj: _.debounce(function () {
                this.isLoading = true;
                this.$store.dispatch('search/fetchSearchApp', {
                    filterKey: this.filterKey,
                    params: this.params
                }).then(appList => {
                    this.appList = this.max ? appList.splice(0, this.max) : appList;
                }).finally(res => {
                    this.isLoading = false;
                    this.$emit('search-ready', this.appList);
                });
            }, 350)
        }
    };
</script>

<style lang="scss" scoped>
    @import "../../assets/css/components/conf.scss";

    .ps-app-list {
        background: #fff;
        max-height: 300px;
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

                .app-name {
                    float: left;
                    width: 60%;
                    text-overflow: ellipsis;
                    overflow: hidden;
                }

                .app-code {
                    color: #C4C6CC;
                    float: right;
                    width: 40%;
                    text-overflow: ellipsis;
                    overflow: hidden;
                    text-align: right;
                }
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
