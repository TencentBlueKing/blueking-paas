<template lang="html">
  <service-general :data="apiData" />
</template>

<script>
    import serviceGeneral from '@/components/serviceGeneral';
    export default {
        components: {
            serviceGeneral
        },
        data () {
            return {
                apiData: {
                    name: this.$t('应用推荐'),
                    apititle: this.$t('应用推荐'),
                    hasLink: true,
                    link: this.GLOBAL.LINK.APP_MARKET,
                    image: '/static/images/recommend.png',
                    apiexplain: this.$t('蓝鲸官方应用市场提供“推荐应用”广告位，帮助您更好的宣传应用'),
                    apiList: []
                }
            };
        }
    };
</script>
