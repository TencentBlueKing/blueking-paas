<template lang="html">
  <div class="overview-tit">
    <div class="title">
      <div>
        <img
          :src="appInfo.logo_url"
          class="overview-title-pic fleft"
        >
        <div
          class="app-collect-btn"
          :class="{ 'marked': curAppInfo.marked }"
          @click="toggleAppMarked"
        >
          <i class="paasng-icon paasng-star-cover" />
        </div>
        <template v-if="appInfo.name">
          <div class="overview-title-text">
            <div class="overflow-app-metedata">
              <strong
                v-bk-overflow-tips
                class="app-title"
              >{{ appInfo.name }}</strong>
              <div
                v-if="platformFeature.REGION_DISPLAY"
                :class="['overview-region region-tag',
                         { inner: appInfo.region === 'ieod', clouds: appInfo.region === 'clouds' }]"
              >
                <span>{{ appInfo.region_name }}</span>
              </div>
            </div>
            <p
              v-bk-overflow-tips
              class="app-code-box"
            >
              {{ appInfo.code }}
            </p>
          </div>

          <div class="dropdown-btn" @click.stop="dropdownShow">
            <a
              href="javascript:"
              class="overview-title-icon"
            >
              <i
                class="paasng-icon right-icon paasng-angle-line-down"
                :class="{ 'right-icon-up': isDropdownShow }"
              />
            </a>
          </div>
        </template>
      </div>


      <div
        v-show="isDropdownShow"
        @click.stop="dropOpen"
        class="nav-dropdown overview-slidedown"
      >
        <div class="quick-access border-box">
          <h3>
            {{ $t('快速访问') }}
            <span style="color: #c4c6cc; font-size: 12px;"> {{ $t('(主模块)') }} </span>
          </h3>
          <template v-if="appDeployed">
            <div class="link">
              <a
                v-if="appLinks.stag"
                :href="appLinks.stag"
                target="_blank"
                class="blue"
              > {{ $t('预发布环境') }} </a>
              <a
                v-if="appLinks.prod"
                :href="appLinks.prod"
                target="_blank"
                class="blue"
              > {{ $t('生产环境') }} </a>
            </div>
          </template>
          <template v-else>
            <p class="no-data">
              {{ engineAbled ? $t('应用暂未部署') : $t('暂无') }}
            </p>
          </template>
          <div
            v-if="showEntrances"
            class="entrances-wrapper"
          >
            <section
              v-for="(item, key, index) in customDomainEntrances"
              v-if="customDomainEntrances[key].length"
              :key="key"
              :class="{ 'set-mt': index !== 0 }"
            >
              <h3>
                {{ $t('独立域名') }}
                <span style="color: #c4c6cc; font-size: 12px;">({{ key === 'stag' ? $t('预发布环境') : $t('生产环境') }})</span>
              </h3>
              <div class="entrances-adress">
                <p
                  v-for="(url, urlIndex) in customDomainEntrances[key]"
                  :key="urlIndex"
                  :class="{ 'set-pb': urlIndex !== customDomainEntrances[key].length - 1 }"
                >
                  <a
                    v-bk-tooltips="{ content: url.hostname, placement: 'left', boundary: 'window' }"
                    :href="url.address"
                    target="_blank"
                    class="address-link blue"
                  >
                    <span style="cursor: pointer;">{{ url.hostname }}</span>
                  </a>
                </p>
              </div>
            </section>
          </div>
        </div>
        <div class="app-dropdown">
          <h3> {{ $t('应用列表') }} ( {{ appList.length }} )</h3>
          <div :class="['paas-search',{ 'focus': isFocused }]">
            <div class="application-search">
              <input
                ref="keywordInput"
                v-model="filterKey"
                type="text"
                :placeholder="$t('输入应用名称、ID，按Enter搜索')"
                @focus="focusInput(true)"
                @blur="focusInput(false)"
                @keydown.down.prevent="searchAppKeyDown"
                @keydown.up.prevent="searchAppKeyUp"
                @keyup.enter="searchApp"
              >
              <span
                v-if="filterKey === ''"
                class="paasng-icon paasng-search input-icon"
              />
              <span
                v-else
                class="paasng-icon paasng-close input-icon"
                @click="clearInputValue"
              />
            </div>
          </div>
          <searchAppList
            ref="searchAppList"
            :filter-key="propsfilterKey"
            :search-apps-router-name="'customed'"
            :params="{ include_inactive: true }"
            @selectAppCallback="selectAppCallback"
            @search-ready="handlerSearchReady"
          />
        </div>
      </div>

    </div>
  </div>
</template>

<script>
import searchAppList from '@/components/searching/searchAppList';
import appBaseMixin from '@/mixins/app-base-mixin';
import { bus } from '@/common/bus';

export default {
  components: {
    searchAppList,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      isFocused: false,
      filterKey: '',
      appList: [],
      appLinks: {
        stag: '',
        prod: '',
      },
      propsfilterKey: '',
      customDomainEntrances: {},
      isDropdownShow: false,
    };
  },
  computed: {
    appInfo() {
      const appInfo = this.$store.state.curAppInfo;
      let logo = '';
      if (appInfo.application && appInfo.application.logo_url) {
        logo = appInfo.application.logo_url;
      } else {
        logo = '/static/images/default_logo.png';
      }
      return {
        logo_url: logo,
        ...appInfo.application,

      };
    },
    appDeployed() {
      return this.appLinks.stag || this.appLinks.prod;
    },
    engineAbled() {
      return this.appInfo.web_config && this.appInfo.web_config.engine_enabled;
    },
    showEntrances() {
      return Object.keys(this.customDomainEntrances).some(key => this.customDomainEntrances[key].length);
    },
    platformFeature() {
      return this.$store.state.platformFeature;
    },
  },
  watch: {
    appInfo() {
      this.initAppList();
    },
    filterKey(newVal, oldVal) {
      if (newVal === '' && oldVal !== '') {
        this.propsfilterKey = '';
        this.$refs.searchAppList.enterSelect();
      }
    },
    appCode() {
      this.getAppLinks();
    },
  },
  mounted() {
    bus.$on('market_switch', () => {
      this.getAppLinks();
    });
    bus.$on('update_entrance', () => {
      this.fetchAppCustomDomainEntrance();
    });
  },
  created() {
    this.getAppLinks();
    this.fetchAppCustomDomainEntrance();
  },
  methods: {
    searchApp() {
      this.propsfilterKey = this.filterKey;
      this.$refs.searchAppList.enterSelect();
    },

    searchAppKeyDown() {
      this.$refs.searchAppList.onKeyDown();
    },

    searchAppKeyUp() {
      this.$refs.searchAppList.onKeyUp();
    },

    async fetchAppCustomDomainEntrance() {
      try {
        const res = await this.$store.dispatch('getAppCustomDomainEntrance', this.$route.params.id);
        const domainEntrances = {
          stag: [],
          prod: [],
        }
                    ;(res || []).forEach((item) => {
          item.addresses.forEach((address) => {
            this.$set(address, 'is_default', item.module.is_default);
          });
          domainEntrances[item.env].push(...item.addresses);
        });
        this.customDomainEntrances = JSON.parse(JSON.stringify(domainEntrances));
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.message,
        });
      }
    },

    // 清空筛选框值
    clearInputValue() {
      this.isFocused = false;
      this.filterKey = '';
      this.propsfilterKey = '';
    },
    focusInput(isFocus) {
      this.isFocused = isFocus;
    },
    // update appLinks when dropdown
    getAppLinks() {
      if (this.curAppInfo.web_config.engine_enabled) {
        ['stag', 'prod'].forEach((env) => {
          this.$store.dispatch('fetchAppExposedLinkUrl', {
            appCode: this.appCode,
            env,
          }).then((link) => {
            this.appLinks[env] = link;
          });
        });
      }
    },
    // 切换APP后的回调方法
    selectAppCallback() {
    //   this.$refs.dropdown.close();
      this.isDropdownShow = false;
    },
    handlerClose() {
      this.filterKey = '';
      this.propsfilterKey = '';
      const addressDom = document.querySelectorAll('.address-link');
      for (const item of addressDom) {
        if (item._tippy) {
          item._tippy.hide();
        }
      }
    },
    handlerOpen() {
      this.$refs.keywordInput.focus();
    },
    // init AppList
    initAppList() {
      this.$refs.searchAppList.fetchObj();
    },
    handlerSearchReady(list) {
      this.fetchAppCustomDomainEntrance();
      this.appList = list;
    },
    // 标记应用
    async toggleAppMarked() {
      if (this.isAppMarking) {
        return false;
      }
      this.isAppMarking = true;
      const appCode = this.curAppInfo.application.code;
      const msg = this.curAppInfo.marked ? this.$t('取消收藏成功') : this.$t('应用收藏成功');

      try {
        await this.$store.dispatch('toggleAppMarked', { appCode, isMarked: this.curAppInfo.marked });
        this.curAppInfo.marked = !this.curAppInfo.marked;
        this.$paasMessage({
          theme: 'success',
          message: msg,
        });
      } catch (error) {
        this.$paasMessage({
          theme: 'error',
          message: this.$t('无法标记应用，请稍后再试'),
        });
      } finally {
        this.isAppMarking = false;
      }
    },


    dropdownShow() {
      this.filterKey = '';
      this.isDropdownShow = !this.isDropdownShow;

      // 监听点击事件
      if (this.isDropdownShow) {
        document.getElementsByTagName('body')[0].className += ' drop-open';
        document.getElementsByClassName('drop-open')[0].addEventListener('click', () => {
          this.isDropdownShow = false;
          document.getElementsByTagName('body')[0].className = 'ps-app-detail';
        });
      } else {
        document.getElementsByTagName('body')[0].className = 'ps-app-detail';
      }
    },
    dropOpen() {
      console.log('stop bubbling');
    },
  },
};

</script>
<style lang="css">
    .ps-nav-dropdown {
        z-index: 110 !important;
    }
</style>
<style lang="scss" scoped>
    @import "../assets/css/components/conf.scss";

    .entrances-wrapper {
        margin-top: 30px;
        .entrances-adress {
            margin-top: 12px;
            p {
              height: 32px;
              line-height: 32px;
            }
            a {
                display: inline-block;
                max-width: 159px;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }
        }
        .set-mt {
            margin-top: 36px;
        }
    }

    .overview-slidedown {
        .paas-search.focus {
            border: 1px solid #3A84FF;
        }
    }

    .overview-title-text {
        display: inline-block;
        margin-top: 3px;

        p {
            font-size: 12px;
            color: #979BA5;
            margin-top: -3px;
            line-height: 12px;
            font-weight: normal;
        }
    }

    .quick-access {
        width: 100%;
        background: #FFF;

        .link {
            margin-top: 9px;
            a {
                font-size: 14px;
                line-height: 28px;
                display: block;
            }
        }

        h3 {
            line-height: 1;
            font-size: 14px;
            color: #313238;
            padding-bottom: 8px;
            font-weight: normal;
            border-bottom: 1px solid #DCDEE5;
        }

    }

    .select-panel {
        position: relative;
    }

    .app-dropdown {
        background: #FFF;

        h3 {
            line-height: 1;
            font-size: 14px;
            color: #313238;
            padding: 17px 20px 8px 20px;
            font-weight: normal;

        }
    }

    .overview-slidedown {
        position: absolute;
        width: 240px;
        top: 60px;
        background: #fff;
        z-index: 9999;
        border: solid 1px #eaeeee;
        border-radius: 0 2px 2px 0;
        left: 0;
        box-shadow: -2px 2px 5px #e5e5e5;
    }

    .overview-slidedown .paas-search {
        position: relative;
        height: 32px;
        line-height: 32px;
        border: solid 1px rgba(196,198,204,1);
        border-radius: 2px;
        margin: 0 20px 10px 20px;
    }

    .overview-slidedown .application-search {
        width: 100%;
        height: 30px;
        line-height: 30px;
    }

    .overview-slidedown .application-search input[type="text"] {
        background: #fff;
        width: 240px;
        height: 30px;
        line-height: 30px;
        cursor: text;
    }

    .overview-slidedown .paas-search.open {
        background: #fff;
    }

    .paas-search.on {
        border: 1px solid #3A84FF;
    }

    .paas-search.open {
        height: auto;
        border-radius: 2px;
        background: #fafafa;
        z-index: 999;
        border: solid 1px #e9edee;
    }

    .application-search-content {
        height: auto;
        border-top: solid 1px #e9edee;
    }

    .application-search-content a {
        display: block;
        height: 32px;
        line-height: 32px;
        padding: 0 13px;
        color: #666666;
    }

    .application-search-content a:hover {
        background: #e9f1fb;
    }

    .application-search {
        width: 198px;
        height: 34px;
        overflow: hidden;
    }

    .application-search input[type="text"] {
        border: none;
        width: 136px;
        padding: 0 10px;
        line-height: 34px;
        height: 34px;
        float: left;
        color: #4f515e;
        background: #fafafa
    }

    .application-search .input-icon {
        position: absolute;
        right: 10px;
        top: 50%;
        margin-top: -6px;
        font-size: 12px;
        color: #C4C6CC;
    }

    .application-search .paasng-close {
        cursor: pointer;
    }

    .overview-title-icon {
        width: 36px;
        height: 60px;
        line-height: 60px;
        text-align: center;
        position: absolute;
        top: 0;
        right: 0;
        transition: all .35s;
        z-index: 99;

        .paasng-icon {
            font-size: 12px;
            font-weight: bold;
            color: #63656E;
            display: inline-block;
            transition: all ease 0.3s;
            transform: scale(0.9);
        }

        &.drop-enabled {
            .paasng-icon {
                transform: rotate(-180deg);
            }
        }

        .right-icon-up{
            transform: rotate(-180deg);
        }
    }

    .overview-title-icon.open {
        background: #fff;
    }

    .overview-title-icon.open:after,
    .overview-title-icon.open:hover:after {
        z-index: 10;
        content: "";
        position: absolute;
        bottom: -1px;
        left: 0;
        width: 59px;
        height: 1px;
        background: #fff;
    }

    .nav-dropdown {
        width: 540px;
        display: flex;

        .quick-access {
            width: 240px;
            min-height: 300px;
            max-height: 380px;
            border-right: 1px solid #DCDEE5;
            padding: 17px 20px;
            overflow-y: auto;
            &::-webkit-scrollbar {
                width: 2px;
                background-color: lighten(transparent, 80%);
            }
            &::-webkit-scrollbar-thumb {
                height: 2px;
                border-radius: 2px;
                background-color: #e6e9ea;
            }
        }

        .app-dropdown {
            width: 300px;
            flex: 1;
        }
    }

    .no-data {
        color: $appMainFontColor;
        padding: 10px 0;
        text-align: left;
    }

    .overview-region {
        position: relative;
        top: -3px;
        margin-left: 2px;
    }

    .region-tag {
        display: inline-block;
        padding: 2px 4px;
        line-height: 16px;
        background: #e7fcfa;
        color: #2dcbae;
        font-size: 12px;
        border-radius: 2px;
        transform: scale(0.8);
        span {
            font-weight: normal;
        }
        &.inner {
            background: #fdefd8;
            color: #ff9c01;
        }
        &.clouds {
            background: #ede8ff;
            color: #7d01ff;
        }
    }
    .app-collect-btn {
        position: absolute;
        width: 16px;
        height: 16px;
        line-height: 14px;
        text-align: center;
        font-size: 11px;
        border-radius: 50%;
        left: 44px;
        top: 38px;
        color: #FFF;
        border: 1px solid #FFF;
        background: #e3e4e8;
        cursor: pointer;

        &.marked {
            background: #FF9C01;
        }
    }

    .app-code-box {
        max-width: 120px;
        overflow: hidden;
        white-space: nowrap;
        text-overflow: ellipsis;
        display: inline-block;
    }

    .title {
        position: relative;
        display: flex;
        justify-content: space-between;
        /deep/ .bk-dropdown-content {
            width: 540px;
            height: 385px;
        }
    }
</style>
