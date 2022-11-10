<template lang="html">
    <div class="right-main">
        <div class="ps-top-bar">
            <h2> {{ $t('持续集成') }} </h2>
        </div>
        <paas-content-loader class="ps-container" :is-loading="!gitReady" placeholder="devops-loading">
            <service-general :data="apiData" :show-title="false"></service-general>
            <git @ready="gitReady = true" style="position: relative; top: -100px;"></git>
        </paas-content-loader>
    </div>
</template>

<script>
    import serviceGeneral from '@/components/serviceGeneral';
    import git from './comps/git';
    export default {
        components: {
            serviceGeneral,
            git
        },
        data () {
            return {
                apiData: {
                    name: this.$t('持续集成'),
                    apititle: this.$t('持续集成'),
                    image: '/static/images/DCloud.png',
                    apiexplain: this.$t('蓝鲸提供源码质量检查，在应用部署之后默认启动，并生成检查报告'),
                    apiList: [
                        {
                            'title': this.$t('代码检查'),
                            'explain': this.$t('蓝鲸使用蓝盾 CodeCC 进行源码检查，为您的应用代码质量保驾护航。')
                        }
                    ]
                },
                gitReady: false
            };
        }
    };
</script>
