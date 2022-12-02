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
            :src="curPluginData.logo"
            onerror="this.src='/static/images/plugin-default.svg'"
          >
          <div class="pl10">
            <div class="plugin-name">
              {{ curPluginData.name_zh_cn }}
            </div>
            <div class="guide-plugin-desc">
              {{ curPluginData.id }}
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
        <bk-input
          v-model="searchValue"
          behavior="simplicity"
          :left-icon="'bk-icon icon-search'"
          :clearable="true"
        />
        <div class="plugin-list">
          <div
            v-for="item in pluginList"
            :key="item.id"
            class="item flex-row align-items-center"
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
        </div>
        <div class="dropdown-footer flex-row align-items-center justify-content-around">
          <div
            class="footer-left item"
            @click="goPage('list')"
          >
            <i class="paasng-icon paasng-arrows-left" />
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
    export default {
        components: {
        },
        data () {
            return {
                showSelectData: false,
                searchValue: '',
                pluginList: [],
                curPluginData: {},
                isHover: false
            };
        },
        watch: {
            pluginList: {
                handler (val) {
                    this.curPluginData = val.find(e => e.id === this.$route.params.id);
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
            changePlugin (data) {
                this.curPluginData = this.pluginList.find(e => e.id === data.id);
                this.$router.push({
                    name: 'pluginVersionManager',
                    params: { pluginTypeId: data.pd_id, id: data.id } // pluginTypeId插件类型标识 id插件标识
                });
                this.hideSelectData();
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
            .plugin-list{
                max-height: 200px;
                overflow-y: auto;
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
</style>
