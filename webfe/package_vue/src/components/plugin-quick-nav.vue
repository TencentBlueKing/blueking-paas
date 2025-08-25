<template>
  <div class="quick-nav">
    <div class="plugin-info">
      <div
        class="cur-plugin flex-row align-items-center justify-content-between"
        @click="hanlerCurPlugin"
      >
        <div class="flex-row align-items-center">
          <img
            :src="curPluginInfo.logo"
            onerror="this.src='/static/images/plugin-default.svg'"
          />
          <div class="pl10">
            <div
              v-bk-overflow-tips
              class="plugin-name ellipsis"
            >
              {{ curPluginInfo.name_zh_cn }}
            </div>
            <div
              v-bk-overflow-tips
              class="guide-plugin-desc"
            >
              {{ curPluginInfo.id }}
            </div>
          </div>
        </div>
        <i
          class="paasng-icon right-icon paasng-angle-line-down"
          :class="{ 'right-icon-up': showSelectData }"
        />
      </div>
      <div
        v-if="showSelectData"
        class="plugin-dropdown"
      >
        <div class="serch-box">
          <bk-input
            v-model="searchValue"
            behavior="simplicity"
            :placeholder="$t('请输入关键字')"
            :left-icon="'bk-icon icon-search'"
            :clearable="true"
            @enter="searchPlugin"
          />
        </div>
        <div class="plugin-list">
          <div v-bkloading="{ isLoading: isLoading, zIndex: 10 }">
            <template v-if="viewPluinList.length">
              <div
                v-for="item in viewPluinList"
                :key="item.id"
                class="item flex-row align-items-center"
                :class="{ 'plugin-active': pluginId === item.id }"
                @click="changePlugin(item)"
              >
                <img
                  :src="item.logo"
                  onerror="this.src='/static/images/plugin-default.svg'"
                />
                <div
                  class="plugin-name ft12 pl10"
                  :title="`${item.name_zh_cn}(${item.id})`"
                >
                  {{ item.name_zh_cn }}
                  ( {{ item.id }} )
                </div>
              </div>
            </template>
            <div
              v-else
              class="not-data-tips"
            >
              {{ pluginList.length ? $t('无匹配数据') : '' }}
            </div>
          </div>
        </div>
        <div class="dropdown-footer flex-row align-items-center justify-content-around">
          <div
            class="footer-left item"
            @click="goPage('list')"
          >
            <i class="paasng-icon paasng-back" />
            {{ $t('插件列表') }}
          </div>
          <div
            class="item"
            @click="goPage('creat')"
          >
            <i class="bk-icon icon-plus-circle" />
            {{ $t('创建插件') }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
<script>
import pluginBaseMixin from '@/mixins/plugin-base-mixin';
import { debounce } from 'lodash';
export default {
  mixins: [pluginBaseMixin],
  data() {
    return {
      showSelectData: false,
      searchValue: '',
      pluginList: [],
      viewPluinList: [],
      isLoading: true,
    };
  },
  computed: {
    pluginId() {
      return this.$route.params.id;
    },
  },
  watch: {
    searchValue() {
      this.searchPlugin();
    },
    showSelectData(val) {
      if (!val) {
        this.searchValue = '';
      }
    },
  },
  created() {
    this.fetchPluginsList();
  },
  methods: {
    async fetchPluginsList() {
      try {
        const pageParams = {
          limit: 1000,
          offset: 0,
        };
        const res = await this.$store.dispatch('plugin/getPlugins', {
          pageParams,
        });
        this.pluginList = res.results;
        this.viewPluinList = res.results;
        // 根据id排序
        this.viewPluinList.sort((a, b) => `${a.id}`.localeCompare(b.id));
      } catch (e) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: e.message,
        });
      } finally {
        this.isLoading = false;
      }
    },
    hanlerCurPlugin() {
      this.showSelectData = !this.showSelectData;
    },
    hideSelectData() {
      this.showSelectData = false;
    },
    goPage(v) {
      this.$router.push({
        name: v === 'list' ? 'plugin' : 'createPlugin',
      });
    },
    async changePlugin(data) {
      // 如果去往当前的路由没有权限则去往概览页
      const parmas = this.getTarget(data.id, data.pd_id);
      this.hideSelectData();
      this.$router.push(parmas);
      // 如果当前为插件版本、测试阶段/测试报告，返回概览页
      if (['pluginVersionRelease', 'pluginTestReport'].includes(this.$route.name)) {
        this.$router.replace({
          name: 'pluginSummary',
          query: {
            id: data.id,
            pluginTypeId: data.pd_id,
          },
        });
      }
    },
    searchPlugin: debounce(function () {
      if (this.searchValue === '') {
        this.viewPluinList = this.pluginList;
      }
      this.viewPluinList = this.pluginList.filter(item => item.name_zh_cn.indexOf(this.searchValue) !== -1 || item.id.indexOf(this.searchValue) !== -1);
    }, 100),

    getTarget(pluginId, pdId) {
      const target = {
        name: this.$route.name,
        params: {
          ...this.$route.params,
          id: pluginId,
          pluginTypeId: pdId,
        },
        query: {
          ...this.$route.query,
        },
      };

      return target;
    },
  },
};
</script>
<style lang="scss" scoped>
@import '~@/assets/css/mixins/ellipsis.scss';
.quick-nav {
  flex-shrink: 0;
  height: 64px;
  border-bottom: 1px solid #e6e9ea;
  cursor: pointer;
  position: relative;
  &:hover {
    background: #f5f7fa;
  }
  .plugin-info {
    height: 100%;
    padding: 6px 16px;
    .cur-plugin {
      img {
        width: 44px;
        height: 44px;
      }
      .plugin-name {
        font-size: 12px;
        font-weight: bold;
        &.ellipsis {
          line-height: 24px;
          @include ellipsis(130px);
        }
      }
      .right-icon {
        font-size: 12px;
        font-weight: bold;
        color: #63656e;
        transition: all ease 0.3s;
        transform: scale(0.9);
      }
      .right-icon-up {
        transform: rotate(-180deg);
      }
    }
    .plugin-dropdown {
      width: 320px;
      position: absolute;
      left: 0;
      top: 58px;
      background: #ffffff;
      border: 1px solid #dcdee5;
      box-shadow: 0 2px 6px 0 rgba(0, 0, 0, 0.1);
      border-radius: 2px;
      z-index: 1000;
      user-select: none;
      .plugin-list {
        padding-top: 5px;
        max-height: 200px;
        overflow-y: auto;
        color: #63656e;
        .item {
          padding: 10px 20px;
          img {
            width: 16px;
            height: 16px;
          }
          .ft12 {
            font-size: 12px;
          }
          .plugin-name {
            width: 100%;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }
        }
        .item:hover {
          background: #e1ecff;
          color: #3a84ff;
        }
      }
      .serch-box {
        padding: 0 7px;
        height: 36px;
        line-height: 36px;
      }
      .dropdown-footer {
        color: #63656e;
        font-size: 12px;
        height: 40px;
        background: #fafbfd;
        border-top: 1px solid #dcdee5;
        border-radius: 0 0 2px 2px;
        .item {
          flex: 1;
          text-align: center;
          height: 40px;
          line-height: 40px;
          i {
            font-size: 16px;
            color: #979ba5;
            transform: translateY(0px);
          }
        }
        .footer-left::after {
          position: absolute;
          content: '';
          width: 1px;
          height: 16px;
          background: #dcdee5;
          bottom: 12px;
          left: 158px;
        }
        .item:hover {
          background: #eeeff3;
        }
      }
    }
    .guide-plugin-desc {
      @include ellipsis(130px);
      font-size: 12px;
      color: #979ba5;
    }
  }
}
.not-data-tips {
  height: 64px;
  display: flex;
  justify-content: center;
  align-items: center;
  color: #666;
}
.plugin-active {
  background: #f5f7fa;
}
</style>
<style>
.quick-nav .plugin-info .plugin-dropdown .left-icon {
  color: #979ba5;
}
.quick-nav .plugin-info .plugin-dropdown .bk-input-text input {
  border-color: transparent transparent #eaebf0 !important;
}
</style>
