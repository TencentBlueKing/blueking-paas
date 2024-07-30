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
        v-if="curDisplayedAppList.length === 0"
        class="no-data"
      >
        <span> {{ filterKey ? $t('无匹配数据'): $t('无应用') }}</span>
      </li>
      <!-- 在顶部导航是需要控制显示应用的个数 -->
      <li
        v-for="(item, index) in curDisplayedAppList"
        :key="index"
        :class="{ 'on': curActiveIndex === index }"
      >
        <a
          href="javascript:void(0);"
          @click="handlerSelectApp(item)"
        >
          <span
            v-bk-overflow-tips
            class="star-icon"
          >
            <i :class="['paasng-icon', item.marked ? 'paasng-star-cover' : 'paasng-star-line']" />
          </span>
          <span
            v-bk-overflow-tips
            class="app-name"
          >
            {{ item.name }}
          </span>
          <span
            v-bk-overflow-tips
            class="app-code"
          >
            {{ item.code }}
          </span>
        </a>
      </li>
    </template>
  </ul>
</template>

<script>
import { debounce, cloneDeep } from 'lodash';
import selectEventMixin from '@/components/searching/selectEventMixin';

export default {
  mixins: [selectEventMixin],
  props: {
    theme: {
      type: [Object, String],
    },
    filterKey: {
      type: String,
    },
    max: {
      type: Number,
    },
    searchAppsRouterName: {
      type: String,
    },
    params: {
      type: Object,
    },
  },
  data() {
    return {
      isLoading: false,
      appList: [],
      curDisplayedAppList: [],
    };
  },
  watch: {
    filterKey() {
      this.curActiveIndex = -1;
      if (this.$route.path.indexOf('/plugin-center') === -1) {
        this.keywordSearch();
      }
    },
  },
  created() {
    if (this.$route.path.indexOf('/plugin-center') === -1) {
      this.init();
    }
  },
  methods: {
    // 拼接当前页新路由地址
    getTarget(appCode, moduleId) {
      const target = {
        name: '',
        params: {
          ...this.$route.params,
          id: appCode,
          moduleId,
        },
        query: {
          ...this.$route.query,
        },
      };
      target.name = (this.searchAppsRouterName === 'customed' ? this.$route.name : 'appSummary');
      if (['monitorAlarm', 'appLog'].includes(this.$route.name)) {
        target.query = {};
      }

      return target;
    },
    init() {
      this.getApplicationList();
    },
    getSelectListLength() {
      return this.curDisplayedAppList.length;
    },
    handlerSelectApp(app) {
      const params = this.getTarget(app.code, app.moduleId);
      // 更新nav
      this.$store.commit('updateNavType', app);
      // 刷新左侧导航(applogo\appname\appcode)
      this.$emit('selectAppCallback');
      this.$router.push(params);
    },
    enterSelect() {
      if (this.curDisplayedAppList.length === 0 || this.curActiveIndex < 0) {
        return;
      }
      const app = this.curDisplayedAppList[this.curActiveIndex];
      // 切换应用后的操作
      this.handlerSelectApp(app);
    },
    handleFetch(res) {
      return this.max ? res.splice(0, this.max) : res;
    },
    // 获取所有应用列表
    getApplicationList() {
      this.isLoading = true;
      this.$store.dispatch('search/fetchSearchApp', {
        filterKey: '',
        params: this.params,
      }).then((appList) => {
        this.appList = appList;
        this.curDisplayedAppList = appList;
        this.$emit('app-filter', this.curDisplayedAppList.length);
      })
        .finally(() => {
          this.isLoading = false;
          this.$emit('search-ready', this.appList);
        });
    },
    keywordSearch: debounce(function () {
      if (!this.filterKey) {
        this.curDisplayedAppList = cloneDeep(this.appList);
      }
      const keyword = this.filterKey.toLocaleLowerCase();
      this.curDisplayedAppList = this.appList.filter((app) => {
        const code = app.code.toLocaleLowerCase();
        const name = app.name.toLocaleLowerCase();
        if (code.includes(keyword) || name.includes(keyword)) {
          return true;
        }
      });
      this.$emit('search-ready', this.curDisplayedAppList);
    }, 300),
  },
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
            font-size: 12px;

            a {
                color: $appMainFontColor;
                font-size: 12px;
                display: block;
                overflow: hidden;
                white-space: nowrap;
                text-overflow: ellipsis;

                .paasng-star-cover {
                  color: #FFB848 !important;
                }

                .star-icon {
                    float: left;
                    margin-right: 10px;
                }

                .app-name {
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
