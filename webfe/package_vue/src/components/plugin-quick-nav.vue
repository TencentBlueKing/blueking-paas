<template>
  <div
    :class="['quick-nav', { 'quick-hover-bg': isHover }]"
    @mouseenter="isHover = true"
    @mouseleave="isHover = false"
  >
    <div class="plugin-info">
      <div
        class="cur-plugin flex-row align-items-center justify-content-between"
        @click="hanlerCurPlugin"
      >
        <div class="flex-row align-items-center">
          <img
            :src="curPluginInfo.logo"
            onerror="this.src='/static/images/plugin-default.svg'"
          >
          <div class="pl10">
            <div class="plugin-name">
              {{ curPluginInfo.name_zh_cn }}
            </div>
            <div class="guide-plugin-desc">
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
            placeholder="请输入关键字"
            :left-icon="'bk-icon icon-search'"
            :clearable="true"
            @enter="searchPlugin"
          />
        </div>
        <div
          class="plugin-list"
        >
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
              >
              <div class="plugin-name ft12 pl10">
                {{ item.name_zh_cn }}
              </div>
              <div class="plugin-desc ft12 pl10">
                ( {{ item.id }} )
              </div>
            </div>
          </template>
          <div
            v-else
            class="not-data-tips"
          >
            {{ $t('无匹配数据') }}
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
    import _ from 'lodash';
    export default {
        components: {
        },
        mixins: [pluginBaseMixin],
        data () {
            return {
                showSelectData: false,
                searchValue: '',
                pluginList: [],
                viewPluinList: [],
                isHover: false,
                isLoading: false
            };
        },
        computed: {
            pluginId () {
                return this.$route.params.id;
            }
        },
        watch: {
            searchValue (newVal, oldVal) {
                this.searchPlugin();
            },
            showSelectData (val) {
                if (!val) {
                  this.searchValue = '';
                }
            }
        },
        created () {
            this.fetchPluginsList();
        },
        methods: {
            async fetchPluginsList () {
                try {
                    const pageParams = {
                        limit: 1000,
                        offset: 0
                    };
                    const res = await this.$store.dispatch('plugin/getPlugins', {
                        pageParams
                    });
                    this.pluginList = res.results;
                    this.viewPluinList = res.results;
                    // 根据id排序
                    this.viewPluinList.sort((a, b) => {
                        return ('' + a.id).localeCompare(b.id);
                    });
                } catch (e) {
                    this.$paasMessage({
                        limit: 1,
                        theme: 'error',
                        message: e.message
                    });
                }
            },
            hanlerCurPlugin () {
                this.showSelectData = !this.showSelectData;
            },
            hideSelectData () {
                this.showSelectData = false;
            },
            goPage (v) {
                this.$router.push({
                    name: v === 'list' ? 'plugin' : 'createPlugin'
                });
            },
            async changePlugin (data) {
                this.$router.push({
                    name: 'pluginVersionManager',
                    params: { pluginTypeId: data.pd_id, id: data.id } // pluginTypeId插件类型标识 id插件标识
                });
                this.hideSelectData();
            },
            searchPlugin: _.debounce(function () {
                if (this.searchValue === '') {
                    this.viewPluinList = this.pluginList;
                }
                this.isLoading = true;
                this.viewPluinList = this.pluginList.filter(item => item.name_zh_cn.indexOf(this.searchValue) !== -1 || item.id.indexOf(this.searchValue) !== -1);
                setTimeout(() => {
                    this.isLoading = false;
                }, 200);
            }, 100),

            getTarget (pluginId, pdId) {
                const target = {
                    name: this.$route.name,
                    params: {
                        ...this.$route.params,
                        id: pluginId,
                        pluginTypeId: pdId
                    },
                    query: {
                        ...this.$route.query
                    }
                };

                return target;
            }
        }
    };
</script>
<style lang="scss" scoped>
.quick-nav{
    border-bottom: 2px solid #F5F7FA;
    cursor: pointer;
    position: relative;
    .plugin-info{
        padding: 6px 16px;
        .cur-plugin{
            img{
                width: 44px;
                height: 44px;
            }
            .plugin-name{
                font-weight: bold;
            }
            .right-icon{
                font-size: 12px;
                font-weight: bold;
                color: #63656E;
                transition: all ease 0.3s;
                transform: scale(0.9);
            }
            .right-icon-up{
                transform: rotate(-180deg);
            }
        }
        .plugin-dropdown{
            width: 320px;
            position: absolute;
            left: 0;
            top: 58px;
            background: #FFFFFF;
            border: 1px solid #DCDEE5;
            box-shadow: 0 2px 6px 0 rgba(0,0,0,0.10);
            border-radius: 2px;
            z-index: 1000;
            user-select: none;
            .plugin-list{
                padding-top: 5px;
                max-height: 200px;
                overflow-y: auto;
                color: #63656E;
                .item {
                    padding: 10px 20px;
                    img{
                        width: 16px;
                        height: 16px;
                    }
                    .ft12{
                        font-size: 12px;
                    }
                }
                .item:hover{
                    background: #E1ECFF;
                    color: #3A84FF;
                }
            }
            .serch-box {
                padding: 0 7px;
                height: 36px;
                line-height: 36px;
            }
            .dropdown-footer{
                color: #63656E;
                font-size: 12px;
                height: 40px;
                background: #FAFBFD;
                border-top: 1px solid #DCDEE5;
                border-radius: 0 0 2px 2px;
                .item {
                    flex: 1;
                    text-align: center;
                    height: 40px;
                    line-height: 40px;
                    i {
                        font-size: 16px;
                        color: #979BA5;
                    }
                }
                .footer-left::after {
                    position: absolute;
                    content: '';
                    width: 1px;
                    height: 16px;
                    background: #DCDEE5;
                    bottom: 12px;
                    left: 158px;
                }
                .item:hover{
                    background: #eeeff3;
                }
            }
        }
    }
}
.quick-hover-bg {
    background: #F5F7FA;
}
.not-data-tips {
    height: 64px;
    display: flex;
    justify-content: center;
    align-items: center;
    color: #666;
}
.plugin-active {
    background: #F5F7FA;
}
</style>
<style>
  .quick-nav .plugin-info .plugin-dropdown .left-icon {
      color: #979BA5;
  }
  .quick-nav .plugin-info .plugin-dropdown .bk-input-text input {
      border-color: transparent transparent #EAEBF0 !important;
  }
</style>
