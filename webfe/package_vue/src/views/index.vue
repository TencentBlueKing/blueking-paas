<template>
  <div class="index-main">
    <div
      v-if="!userHasApp"
      class="paas-banner"
    >
      <div class="paas-text">
        <img
          src="/static/images/yahei-5.png"
          class="appear"
        />
      </div>
      <router-link
        :to="{ name: 'createApp' }"
        class="paas-banner-button appear"
      >
        {{ homePageStaticInfo.data.banner_btn.text }}
      </router-link>
      <router-link
        v-if="userFeature.MGRLEGACY"
        :to="{ name: 'appLegacyMigration' }"
        class="btn-link spacing-h-x2"
      >
        {{ $t('迁移旧版应用') }}
      </router-link>
      <router-link
        v-if="isShowOffAppAction"
        :to="{ name: 'myApplications' }"
        style="margin-left: 0"
        class="btn-link spacing-h-x2"
      >
        {{ $t('查看已下架应用') }}
      </router-link>
    </div>
    <div
      v-if="userHasApp"
      class="paas-content home-content"
    >
      <div class="wrap">
        <paas-content-loader
          :is-loading="isLoading"
          placeholder="index-loading"
          :offset-top="0"
          :height="378"
          data-test-id="developer_header_content"
        >
          <!-- 应用总览 -->
          <home-app-overview />

          <!-- 应用闲置看板功能/告警记录/最近操作记录 -->
          <home-content />
        </paas-content-loader>
      </div>
    </div>

    <!-- 中间部分 start -->
    <div
      class="paas-content home-content"
      data-test-id="developer_content_wrap"
      v-if="!userHasApp"
    >
      <div class="wrap guide-content">
        <!-- 新手入门&使用指南 start -->
        <div
          class="paas-content-boxpanel"
          data-test-id="developer_list_info"
        >
          <div class="paas-modular fleft">
            <h2 class="paas-modular-title">
              {{ $t('新手入门') }}
            </h2>
            <div
              v-for="(item, index) in homePageStaticInfo.data.new_user.list"
              :key="index"
              class="paas-question"
            >
              <a
                :href="item.url"
                target="_blank"
                class="paas-ask"
              >
                {{ item.title }}
              </a>
              <p>{{ item.info }}</p>
            </div>
          </div>
          <div class="paas-modular fright">
            <h2 class="paas-modular-title">
              {{ $t('使用指南') }}
            </h2>
            <div
              v-for="(item, index) in homePageStaticInfo.data.guide_info.list"
              :key="index"
              class="paas-question"
            >
              <a
                :href="item.url"
                target="_blank"
                class="paas-ask"
              >
                {{ item.title }}
                <i
                  v-if="item.icon"
                  class="paasng-icon paasng-play"
                />
              </a>
              <p>{{ item.info }}</p>
            </div>
          </div>
        </div>
        <!-- 新手入门&使用指南 end -->
      </div>
    </div>
  </div>
</template>

<script>
import auth from '@/auth';
import { bus } from '@/common/bus';
import homeContent from '@/views/dev-center/home/home-content/index.vue';
import appOverview from '@/views/dev-center/home/app-overview/index.vue';
import { psIndexInfo, psHeaderInfo } from '@/mixins/ps-static-mixin';

export default {
  components: {
    homeContent,
    homeAppOverview: appOverview,
  },
  mixins: [psIndexInfo, psHeaderInfo],
  data() {
    return {
      userHasApp: false,
      flag: false,
      isShowOffAppAction: false,
      isLoading: true,
    };
  },
  computed: {
    userFeature() {
      return this.$store.state.userFeature;
    },
  },
  // Get userHasApp before render
  beforeRouteEnter(to, from, next) {
    const promise = auth.requestHasApp();
    promise.then((userHasApp) => {
      next((vm) => {
        vm.setUserHasApp(userHasApp);
        if (!userHasApp) {
          auth.requestOffApp().then((flag) => {
            vm.isShowOffAppAction = flag;
          });
        }
      });
    });
  },
  beforeRouteUpdate(to, from, next) {
    const promise = auth.requestHasApp();
    promise.then((userHasApp) => {
      this.setUserHasApp(userHasApp);
      next(() => {
        if (!userHasApp) {
          auth.requestOffApp().then((flag) => {
            this.isShowOffAppAction = flag;
          });
        }
      });
    });
  },
  created() {
    bus.$on('on-close-loading', () => {
      this.isLoading = false;
    });
  },
  methods: {
    setUserHasApp(value) {
      this.userHasApp = value;
      if (!value) {
        bus.$emit('page-header-be-transparent');
      }
    },
  },
};
</script>
<style lang="scss" scoped>
@import '~@/assets/css/mixins/ellipsis.scss';
.paas-content.home-content {
  background-color: #f5f7fa;
  .guide-content {
    width: 1200px;
    margin: 0 auto;
  }
}

.paas-highcharts {
  width: 50%;
  position: relative;

  h3 {
    text-align: center;
    position: absolute;
    width: 100%;
    font-size: 16px;
    font-weight: normal;
  }
}

.paas-banner {
  width: 100%;
  height: 420px;
  background: url(/static/images/banner.jpg) top center no-repeat;
  text-align: center;
  background-color: #191828;

  .paas-text {
    text-align: center;
    font-size: 24px;
    line-height: 40px;
    color: #fff;
    padding-top: 172px;
  }

  .paas-banner-button {
    display: inline-block;
    color: #fff;
    font-size: 18px;
    line-height: 54px;
    text-align: center;
    width: 220px;
    border-radius: 27px;
    background: #3976e4;
    margin: 47px auto;
    transition: all 0.5s;

    &:hover {
      background: #3369cc;
      transtion: all 0.5s;
    }
  }
}

.paas-operation-section {
  &.time-section {
    padding: 0;
    width: 100px;
    @include ellipsis;
  }
  &.section1 {
    width: 210px;

    a {
      padding-left: 11px;
      color: #63656e;
      display: inline-block;
      overflow: hidden;
      line-height: 38px;
      vertical-align: middle;
      text-overflow: ellipsis;

      .spantext {
        padding-left: 10px;
        max-width: 138px;
        font-weight: bold;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        display: inline-block;
      }

      &:hover {
        color: #3a84ff;
      }
    }
  }

  &.section2 {
    width: 350px;
    text-align: left;

    span {
      color: #63656e;
      &.module-name {
        margin-right: 3px;
        font-weight: bold;
      }
    }

    // 对齐显示操作
    em {
      display: inline-block;
    }
  }

  &.fright {
    float: right;

    a {
      padding: 0 20px;
      font-size: 14px;
    }
  }
}

.ps-btn-disabled-new {
  height: 32px;
  color: #dcdee5 !important;
  background: #fafbfd;
  cursor: not-allowed;
  .paasng-icon {
    color: #dcdee5 !important;
  }
}

.section-button-new {
  padding: 0 12px;
  width: 100px;
  height: 30px;
  line-height: 30px;
  border-radius: 2px;
  font-size: 14px;
  color: #2dcb56;
  background: #dcffe2;
  -moz-transition: all 0.5s;
  -ms-transition: all 0.5s;
  -webkit-transition: all 0.5s;
  transition: all 0.5s;
  .paasng-icon {
    position: relative;
  }
}

.section-button-new:hover {
  color: #fff;
  background: #2dcb56;
  .paasng-icon {
    color: #fff;
  }
}

.disabledBox .section-button-new:hover {
  color: #4fb377;
  background: #eefaf3;
}

.open .section-button-new {
  .paasng-icon {
    left: 30px;
    transition: left 0.5s ease-in 0.1s;
    color: #2dcb56;
  }
}

.section-button-new img {
  padding-left: 6px;
  vertical-align: middle;
  position: relative;
  top: -1px;
}

.open .section-button-new {
  background: #fff;
  color: #666666;
  text-align: left;
  padding: 0 12px;
  display: block;
}

.open .section-button-new img {
  position: absolute;
  top: 14px;
  right: 12px;
}

.section-box {
  position: absolute;
  top: 4px;
  padding: 0;
  width: 100px;
  height: 30px;
  line-height: 30px;
  border-radius: 2px;
  border: solid 1px #eefaf3;
  transition: all 0.5s;
  background-color: white;
  overflow: hidden;
}

.open .section-box {
  height: auto;
  border: solid 1px #e9edee;
  border-radius: 2px;
  z-index: 99;
  border-color: #3a84ff;
  box-shadow: 0 4px 8px -4px rgba(0, 0, 0, 0.1), 0 -4px 8px -4px rgba(0, 0, 0, 0.1);
}

.section-button-down {
  min-width: 110px;
  width: auto;

  a {
    line-height: 34px;
    padding: 0 10px;
    display: block;
    height: 34px;
    color: #63656e;
    cursor: pointer;

    &:hover {
      background: #dcffe2;
      color: #2dcb56;
    }
  }
}

.paasng-angle-up,
.paasng-angle-down {
  padding-left: 3px;
  transition: all 0.5s;
  font-size: 12px;
  font-weight: bold;
  color: #5bd18b;
}

.open .section-button .paasng-angle-down {
  position: absolute;
  top: 8px;
  right: 12px;
}

.paas-highcharts {
  width: 560px;
  height: 275px;
}

.paas-modular {
  width: 540px;

  .paas-question {
    line-height: 24px;
    color: #63656e;
    min-height: 100px;
    .paas-ask {
      display: block;
      padding: 14px 0;
      color: #3a84ff;
      font-size: 16px;

      &:hover {
        color: #3a84ff;
      }

      img {
        vertical-align: top;
        line-height: 24px;
        padding: 4px 0 0 4px;
      }
    }
  }
}

.paas-modular-title {
  font-size: 30px;
  color: #4f515e;
  line-height: 40px;
  font-weight: normal;
  padding: 10px 0;
}

.paas-help {
  width: 100%;
  overflow: hidden;
  padding: 25px 0 13px 0;

  .advantage-detail {
    padding: 40px 50px;
    border: 1px solid #ccc;
    margin-right: -1px;
    width: 50%;
    float: left;
    cursor: default;
    box-sizing: border-box;
    height: 214px;

    .advantage-detail-title {
      font-size: 20px;
      color: #333;
      line-height: 1;

      img {
        vertical-align: top;
        margin-right: 19px;
      }

      .advantage-detail-title-line {
        transition: all 0.35s;
        width: 35px;
        border: 1px solid #3a84ff;
        top: 0;
        left: 0;
        margin-top: 30px;
        margin-left: 50px;
      }

      &:hover {
        .advantage-detail-title-line {
          width: 78px;
        }
      }
    }

    .describe-text {
      margin-top: 12px;
      margin-left: 50px;

      a {
        display: block;
        color: #63656e;
        line-height: 30px;
        transition: all 0.35s;

        &:hover {
          color: #3a84ff;
        }
      }
    }
  }
}

.paas-resource {
  display: flex;
  margin-left: -16px;
  margin-right: -16px;
  color: #999;
  text-align: center;

  li {
    width: 370px;
    height: 198px;
    margin: 0 16px;
    border: solid 1px #e9edee;
    box-shadow: 0 2px 4px #eee;
    overflow: hidden;
    transition: all 0.5s;
    float: left;
    border-radius: 2px;

    &:hover {
      border: solid 1px #3a84ff;
    }

    .paas-resource-title {
      line-height: 50px;
      height: 50px;
      overflow: hidden;
      padding: 0 10px;
      border-bottom: solid 1px #e9edee;
      color: #63656e;
      font-size: 16px;
    }

    .resource-text {
      padding: 28px 0 0 0;
      line-height: 60px;

      span {
        font-size: 60px;
        color: #3a84ff;
        line-height: 60px;
        font-family: 'PingFang';
      }
    }
  }
}

.paas-service {
  padding-top: 30px;
  overflow: hidden;

  .paas-service-list {
    width: 100%;
    overflow: hidden;
    display: flex;

    li {
      width: 20%;
      float: left;
      height: 117px;
      border-top: solid 3px #fafafa;
      text-align: center;
      cursor: pointer;
      transition: all 0.35s;

      &.active {
        border-top: solid 3px #3a84ff;
        background: #e9edee;
      }

      &:hover {
        background: #e9edee;
      }

      .paas-service-text {
        display: block;
        font-size: 20px;
        color: #333;
        line-height: 28px;
        padding: 10px 0 0 0;
      }

      .paas-service-icon {
        height: 45px;
        display: inline-block;
        margin: 16px auto 0;
        background: url(/static/images/service-icon3.png) no-repeat;

        &.icon1 {
          width: 67px;
          background-position: 0 0;
        }

        &.icon2 {
          width: 68px;
          background-position: -194px 0;
        }

        &.icon3 {
          width: 68px;
          background-position: -391px 0;
        }

        &.icon4 {
          width: 67px;
          background-position: -592px 0;
        }

        &.icon5 {
          width: 67px;
          background-position: -785px 0;
        }

        &.icon6 {
          width: 67px;
          background-position: -985px 0;
        }
      }
    }
  }

  .paas-service-main {
    width: 100%;
    overflow: hidden;

    .paas-service-content {
      width: 7080px;
      display: flex;
      overflow: hidden;
      margin-left: 0;
      transition: all 0.5s;

      &.showCon {
        margin-left: 0;
      }

      &.showCon1 {
        margin-left: -100%;
      }

      &.showCon2 {
        margin-left: -200%;
      }

      &.showCon3 {
        margin-left: -300%;
      }

      &.showCon4 {
        margin-left: -400%;
      }

      &.showCon5 {
        margin-left: -500%;
      }

      .content-panel {
        background: #e9edee;
        overflow: hidden;
        padding: 9px 0 17px 0;
        width: 1180px;

        dl {
          display: inline-block;
          width: 219px;
          padding: 10px 38px;
          vertical-align: text-top;
        }

        dt {
          font-size: 18px;
          color: #4f515e;
          line-height: 38px;

          a {
            color: #333;
            transition: all 0.5s;

            &:hover {
              color: #3a84ff;
            }
          }
        }

        dd {
          color: #999;
          line-height: 18px;
        }
      }
    }
  }
}

.appear {
  animation: opacity_show 0.85s 1 cubic-bezier(0.445, 0.05, 0.55, 0.95) forwards;
  opacity: 1 !important;
}

@keyframes opacity_show {
  0% {
    transform: translateY(50px);
    opacity: 0.1;
  }

  100% {
    transform: translateY(0);
    opacity: 1;
  }
}

.migration-legacy {
  padding-right: 20px;
}

.migration-legacy-at-applist {
  position: absolute;
  right: 450px;
}

.ps-table-app {
  color: #63656e;

  &:hover {
    color: #3a84ff;
  }
}

.legacy-links {
  font-size: 14px;
}

.ps-btn-visit-disabled .paasng-angle-down,
.ps-btn-visit:disabled .paasng-angle-down,
.ps-btn-visit[disabled] .paasng-angle-down {
  color: #d7eadf !important;
}

.wrap {
  margin: 24px 40px auto;
}
.section-wrapper {
  display: flex;
  white-space: nowrap;
}
.text-style {
  display: inline-block;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.access-module-custom {
  background: #f0f1f5;
  border: none;

  &.is-focus {
    background: #fff;
    border: 1px solid #3a84ff;
    box-shadow: none;
    &:hover {
      background: #fff;
    }
  }

  &:hover {
    background: #eaebf0;
  }
}
</style>
<style lang="scss">
.access-module-popover-custom {
  .bk-options .bk-option .bk-option-content {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .bk-options .bk-option.is-selected + .bk-option {
    margin-top: 6px !important;
  }
}
</style>
