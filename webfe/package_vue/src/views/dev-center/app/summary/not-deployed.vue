<template lang="html">
  <div
    id="summary"
    class="right-main"
  >
    <div class="overview-tit">
      <h2> {{ $t('应用概览') }} </h2>
    </div>
    <div class="middle">
      <div class="coding">
        <h2> {{ $t('应用尚未部署，暂无运行数据！') }} </h2>
        <p> {{ $t('你可以根据以下操作解决此类问题') }} </p>
        <p class="checkout_center">
          <a
            :href="trunkUrl"
            class="checkout ibtn icheckout"
          > {{ $t('签出应用代码') }} </a>
          <a
            href="javascript:"
            class="checkout ibtn"
          > {{ $t('部署至预发布环境') }} </a>
        </p>
      </div>
    </div>
  </div>
</template>

<script>
    export default {
        data () {
            return {
                trunkUrl: '',
                appCode: this.$route.params.id
            };
        },
        created () {
            this.init();
        },
        init () {
            this.appCode = this.$route.params.id;
            const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/`;
            this.$http.get(url).then((response) => {
                const resData = response;
                this.trunkUrl = resData.repo.trunk_url;
            });
        }
    };
</script>
