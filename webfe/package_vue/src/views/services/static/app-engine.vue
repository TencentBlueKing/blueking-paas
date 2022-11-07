<template lang="html">
    <service-general :data="apiData"></service-general>
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
                    name: this.$t('应用引擎'),
                    apititle: this.$t('应用引擎'),
                    image: '/static/images/app-engine.png',
                    apiexplain: this.$t('蓝鲸PaaS平台提供的多语言应用引擎'),
                    apiList: [
                        {
                            'title': this.$t('多语言'),
                            'explain': this.$t('支持包含 Python、Go、Node.js 在内的多种编程语言')
                        },
                        {
                            'title': this.$t('弹性扩缩容'),
                            'explain': this.$t('应用引擎为蓝鲸应用提供了强大的扩缩容能力。应用开发者无需担心访问量增长带来的容量问题，一切都可以交由应用引擎处理')
                        }
                    ]
                }
            };
        }
    };
</script>
