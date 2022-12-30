<template>
    <content-loader
        :width="baseWidth"
        :style="{ 'transform': `scaleX(${contentWidth / baseWidth})` }"
        :height="571"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor">
        <rect x="0" y="0" rx="2" ry="2" :width="130" height="30" />
        <rect x="0" y="58" rx="2" ry="2" :width="baseWidth" height="30" />
        <rect x="20" y="116" rx="2" ry="2" :width="100" height="30" />
        <rect x="140" y="116" rx="2" ry="2" :width="400" height="30" />
        <rect x="20" y="174" rx="2" ry="2" :width="100" height="30" />
        <rect x="140" y="174" rx="2" ry="2" :width="400" height="30" />
        <rect x="20" y="232" rx="2" ry="2" :width="100" height="30" />
        <rect x="140" y="232" rx="2" ry="2" :width="400" height="30" />
        <rect x="20" y="290" rx="2" ry="2" :width="100" height="30" />
        <rect x="140" y="290" rx="2" ry="2" :width="400" height="30" />
        <rect x="20" y="348" rx="2" ry="2" :width="100" height="30" />
        <rect x="140" y="348" rx="2" ry="2" :width="400" height="30" />
        <rect x="20" y="406" rx="2" ry="2" :width="100" height="30" />
        <rect x="140" y="406" rx="2" ry="2" :width="400" height="30" />
        <rect x="140" y="464" rx="2" ry="2" width="140" height="48" />
    </content-loader>
</template>
<script>
    import { ContentLoader } from 'vue-content-loader'
    export default {
        components: {
            ContentLoader
        },
        props: {
            baseWidth: {
                type: Number,
                default: 1180
            },
            contentWidth: {
                type: Number,
                default: 1180
            }
        },
        computed: {
            loadingConf () {
                return this.$store.state.loadingConf
            }
        }
    }
</script>
