<template lang="html">
  <footer class="ps-sample-footer">
    <div class="info" v-dompurify-html="footerInfo"></div>
    <div>{{ platformConfig.footerCopyrightContent }}</div>
  </footer>
</template>

<script>
export default {
  data() {
    return {
    };
  },
  computed: {
    platformConfig() {
      return this.$store.state.platformConfig;
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
    footerInfo() {
      return this.platformConfig.i18n?.footerInfoHTML;
    },
  },
};
</script>

<style lang="scss" scoped>
// ps-sample
.ps-sample-footer {
  text-align: center;
  width: 100%;
  margin: 0 auto;
  color: #63656e;
  font-size: 12px;
  padding: 15px 0;
  background: #f5f7fa;
  .info {
    margin-bottom: 6px;
  }
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
