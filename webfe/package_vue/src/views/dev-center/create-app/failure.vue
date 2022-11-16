<template lang="html">
  <div class="paas-content white">
    <div class="wrap">
      <div class="establish-success">
        <!-- 创建成功 start -->
        <div class="establish-success-fleft">
          <i class="paasng-icon paasng-close-circle-shape text-fail" />
          <h2> {{ $t('创建失败') }} </h2>
          <p>
            {{ $t('很遗憾！您的') }} <a
              href="javascript:"
              class="blue"
            >{{ appname }}</a> {{ $t('应用创建失败') }}
          </p>
          <p class="fail-reason">
            {{ reason }}
          </p>
          <p>
            <router-link
              :to="{ name: 'createApp' }"
              class="ps-btn ps-btn-primary ps-btn-l"
            >
              {{ $t('重试') }}
            </router-link>
          </p>
        </div>
        <!-- 创建成功 end -->

        <!-- 帮助 start -->
        <div class="overview-sub-fright">
          <dl class="overview-sub-dl">
            <dt> {{ $t('帮助') }} </dt>
            <dd>
              <a
                href="javascript:"
                class="blue"
              > {{ $t('如何搭建本地开发环境？') }} </a>
            </dd>
            <dd>
              <a
                href="javascript:"
                class="blue"
              > {{ $t('如何部署蓝鲸应用？') }} </a>
            </dd>
            <dd>
              <a
                href="javascript:"
                class="blue"
              > {{ $t('如何使用蓝鲸开发框架？') }} </a>
            </dd>
          </dl>
        </div>
        <!-- 帮助 end -->
      </div>
    </div>
  </div>
</template>

<script>
    export default {
        data () {
            return {
                appname: '',
                reason: ''
            };
        },
        created () {
            const getAppInfo = window.location.search.split('&');
            this.appname = decodeURI(getAppInfo[0].split('=')[1].toString());
            this.reason = decodeURI(getAppInfo[1].split('=')[1].toString());
        }
    };
</script>

<style lang="scss" scoped>
    .establish-success {
        overflow: hidden;
        position: relative;
        padding-top: 48px;
        height: 800px;
    }

    .establish-success-fleft {
        width: 740px;
        padding: 0 100px 0 80px;
    }

    .establish-success-fleft h2 {
        color: #333;
        font-size: 22px;
        line-height: 40px;
        font-weight: normal;
    }

    .overview-sub-fright {
        width: 260px;
        min-height: 741px;
        border-left: none;
        position: absolute;
        padding: 0 20px;
        top: 60px;
        right: 0;
        padding-bottom: 9999px;
    }

    .overview-sub-dl dt {
        font-size: 14px;
        color: #52525d;
        font-weight: bold;
        padding: 4px 0 14px 0;
    }

    .overview-sub-dl dd a {
        font-size: 14px;
        padding: 4px 0;
    }

    .paasng-close-circle-shape {
        font-size: 58px;
        position: absolute;
        left: 0;
        top: 52px;
    }

    .fail-reason {
        padding: 38px 0 14px 0;
        margin-left: 5em;
        text-indent: -5em;
    }

    .fail-btn {
        width: 120px;
        height: 42px;
        line-height: 42px;
    }
</style>
