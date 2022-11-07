<template>
    <content-loader
        :width="baseWidth"
        :style="{ 'transform': `scaleX(${contentWidth / baseWidth})` }"
        :height="328"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor"
        >
        <rect x="0" y="0" rx="2" ry="2" :width="baseWidth" height="42" /> 
        <rect x="0" y="55" rx="1" ry="1" :width="baseWidth" height="20" /> 
        <rect x="0" y="96" rx="1" ry="1" :width="baseWidth" height="20" /> 
        <rect x="0" y="127" rx="1" ry="1" :width="baseWidth" height="20" /> 
        <rect x="0" y="168" rx="1" ry="1" :width="baseWidth" height="20" /> 

        <rect x="0" y="230" rx="1" ry="1" width="100" height="20" /> 
        <rect x="0" y="260" rx="1" ry="1" :width="baseWidth" height="100" /> 
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
