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
                    name: 'AppRocket',
                    apititle: 'AppRocket',
                    hasLink: true,
                    link: this.GLOBAL.LINK.APP_ROCKET,
                    image: '/static/images/AppRocket.png',
                    apiexplain: this.$t('蓝鲸Model在线生成器服务，基于Django框架，支持在线配置Django Model模型，一键生成对应Python代码'),
                    apiList: [
                        {
                            'title': this.$t('在线定义Model'),
                            'explain': this.$t('支持在线定义Django Model，并自定义Model字段，支持常用字段类型。')
                        },
                        {
                            'title': this.$t('在线生成源代码'),
                            'explain': this.$t('支持在线一键生成Model源代码，您可在线查看、编辑、下载代码，集成到蓝鲸应用中。')
                        },
                        {
                            'title': this.$t('帮助文档：'),
                            'explain': this.$t('Django Model生成器使用入门'),
                            'explainIsLink': true,
                            'url': this.GLOBAL.LINK.APP_ROCKET
                        }
                    ]
                }
            };
        }
    };
</script>
