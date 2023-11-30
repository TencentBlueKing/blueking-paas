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
                    name: this.$t('运维开发工具'),
                    hasLink: true,
                    link: this.GLOBAL.LINK.LESSCODE_INDEX,
                    apititle: this.$t('运维开发工具'),
                    image: '/static/images/service-pic8.png',
                    apiexplain: this.$t('蓝鲸智云运维开发平台提供了前端页面在线可视化拖拽组装、配置编辑、源码生成、二次开发等能力。旨在帮助用户通过尽量少的手写代码的方式快速设计和开发 SaaS'),
                    apiList: [
                        {
                            'title': this.$t('可视化拖拽布局'),
                            'explain': this.$t('集成蓝鲸 MagicBox Vue 通用组件，支持在线画布拖拽组件进行页面布局编辑、在线预览、查看及下载源码。')
                        },
                        {
                            'title': this.$t('布局模板'),
                            'explain': this.$t('提供多种导航布局模板。')
                        },
                        {
                            'title': this.$t('在线函数库管理'),
                            'explain': this.$t('支持在线灵活编写管理事件函数及远程接口返回数据清洗函数。')
                        },
                        {
                            'title': this.$t('在线组件配置'),
                            'explain': this.$t('支持组件样式、属性、事件在线配置。')
                        },
                        {
                            'title': this.$t('二次开发能力'),
                            'explain': this.$t('生成的 Vue 源码文件支持无缝集成到蓝鲸前端开发框架(BKUI-CLI)进行二次开发。')
                        },
                        {
                            'title': this.$t('支持自定义组件开发'),
                            'explain': this.$t('提供自定义组件开发规范及示例，开放自定义组件开发能力，满足业务场景组件集成需求。')
                        },
                        {
                            'title': this.$t('一键部署'),
                            'explain': this.$t('基于蓝鲸PaaS，支持在线拖拽布局后，一键部署至线上环境。')
                        }
                    ]
                }
            };
        }
    };
</script>
