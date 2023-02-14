<template lang="html">
  <footer class="ps-sample-footer">
    <template v-if="GLOBAL.APP_VERSION === 'te'">
      <div class="info">
        <bk-link
          theme="primary"
          :href="GLOBAL.LINK.BK_HELP"
          target="_blank"
        >
          {{ $t('联系BK助手') }}
        </bk-link>
        |
        <bk-link
          theme="primary"
          :href="GLOBAL.LINK.BK_DESKTOP"
          target="_blank"
        >
          {{ $t('蓝鲸桌面') }}
        </bk-link>
      </div>
      <div>Copyright © 2012-{{ curYear }} Tencent BlueKing. All Rights Reserved.</div>
    </template>
    <template v-else>
      <div class="info">
        <bk-link
          theme="primary"
          href="https://wpa1.qq.com/KziXGWJs?_type=wpa&qidian=true"
          target="_blank"
        >
          {{ $t('技术支持') }}
        </bk-link>
        |
        <bk-link
          theme="primary"
          href="https://bk.tencent.com/s-mart/community/"
          target="_blank"
        >
          {{ $t('社区论坛') }}
        </bk-link>
        |
        <bk-link
          theme="primary"
          href="https://bk.tencent.com/"
          target="_blank"
        >
          {{ $t('产品官网') }}
        </bk-link>
      </div>
      <div>Copyright © 2012-{{ curYear }} Tencent BlueKing. All Rights Reserved. {{ paasVersion }}</div>
    </template>
  </footer>
</template>

<script>
    export default {
        data () {
            return {
                bkPaas2Url: window.BK_PAAS2_URL
            };
        },
        computed: {
            curYear () {
                return (new Date()).getFullYear();
            },
            routeName () {
                return this.$route.name;
            },
            useCenterStyle () {
                return ['index', 'myApplications'].includes(this.routeName);
            },
            paasVersion () {
                return window.BK_PAAS_VERSION;
            }
        }
    };
</script>

<style lang="scss" scoped>
// ps-sample
.ps-sample-footer {
  text-align: center;
  width: 100%;
  // margin: 25px auto;
  margin: 15px auto;
  color: #63656e;
  font-size: 12px;
}

// ps-footer
.ps-footer{
  background: #191929;
  padding: 44px 80px;
  overflow: hidden;
}
.ps-footer .wrap{
  position: relative;

  &.center {
    width: 1180px;
    margin: auto;
    text-align: left;
  }
}
.ps-footer-copy{
  width: 451px;
  float: left;
  border-right: solid 1px #2c2d3c;
  font-size: 12px;
  color: #9394a3;
  line-height: 20px;
}
.ps-footer-logo{
  padding: 16px 0 20px 0;
}
.ps-footer-nav{
  position: absolute;
  right: -60px;
  top: 0;
  padding-left: 69px;
}
.ps-footer-nav dl{
  float: left;
  padding: 0 60px;
}
.ps-footer-nav dt{
  line-height: 36px;
  color: #ffffff;
  font-weight: bold;
  padding-top: 4px;
}
.ps-footer-nav dd a{
  color: #9394a3;
  line-height: 24px;
}
.ps-footer-nav dd a:hover{
  color: #3A84FF;
}
</style>
