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
                    name: this.$t('数据视图'),
                    apititle: this.$t('蓝鲸数据可视化服务'),
                    hasLink: true,
                    link: this.GLOBAL.LINK.DATA_INDEX,
                    image: '/static/images/widget.png',
                    apiexplain: this.$t('蓝鲸数据可视化服务'),
                    apiList: [
                        {
                            'title': this.$t('widget配置'),
                            'explain': this.$t('单视图Widget配置，支持线图、饼图等多种图表配置。'),
                            'url': this.GLOBAL.LINK.DATA_WIDGET_INDEX
                        },
                        {
                            'title': this.$t('视图面板配置'),
                            'explain': this.$t('支持在线拖拽，自定义布局视图面板。'),
                            'url': this.GLOBAL.LINK.DATA_DASHBOARD_INDEX
                        }
                    ]
                }
            };
        }
    };
</script>

<style media="screen" lang="scss" scoped>
    .paasng-angle-double-right {
        padding-left: 3px;
        font-size: 12px;
        font-weight: bold;
    }
</style>
