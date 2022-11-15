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
                    name: this.$t('应用市场'),
                    apititle: this.$t('蓝鲸应用市场'),
                    hasLink: true,
                    link: this.GLOBAL.LINK.APP_MARKET,
                    image: '/static/images/market.png',
                    apiexplain: this.$t('蓝鲸应用市场汇集所有在蓝鲸上开发的WEB类应用，用户可以在市场中搜索、使用应用'),
                    apiList: []
                }
            };
        }
    };
</script>
