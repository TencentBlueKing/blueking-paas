<template>
    <content-loader
        :width="baseWidth"
        :style="{ 'transform': `scaleX(${contentWidth / baseWidth})` }"
        :height="571"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor">
        <rect x="0" y="0" rx="2" ry="2" :width="130" height="26" />
        <rect x="20" y="48" rx="2" ry="2" :width="100" height="30" />
        <rect x="140" y="48" rx="2" ry="2" :width="700" height="30" />
        <rect x="20" y="90" rx="1" ry="1" :width="100" height="30" />
        <rect x="140" y="90" rx="1" ry="1" :width="700" height="30" />
        <rect x="20" y="132" rx="1" ry="1" :width="100" height="30" />
        <rect x="140" y="132" rx="1" ry="1" :width="120" height="30" />
        <rect x="280" y="132" rx="1" ry="1" :width="120" height="30" />
        <rect x="420" y="132" rx="1" ry="1" :width="120" height="30" />
        <rect x="20" y="174" rx="1" ry="1" :width="100" height="30" />
        <rect x="140" y="174" rx="1" ry="1" :width="700" height="30" />
        <rect x="20" y="216" rx="1" ry="1" :width="100" height="30" />
        <rect x="140" y="216" rx="1" ry="1" :width="700" height="100" />
        <rect x="140" y="340" rx="2" ry="2" width="130" height="28" />
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
