<template>
    <content-loader
        :width="baseWidth"
        :style="{ 'transform': `scaleX(${contentWidth / baseWidth})` }"
        :height="328"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor"
        >
        <rect x="0" y="0" rx="1" ry="1" width="73" height="16" /> 
        <rect x="0" y="108" rx="1" ry="1" width="73" height="16" /> 
        <rect x="0" y="36" rx="1" ry="1" width="258" height="16" /> 
        <rect x="0" y="144" rx="1" ry="1" width="440" height="16" /> 
        <rect x="0" y="56" rx="2" ry="2" width="144" height="32" /> 
        <rect x="0" y="166" rx="2" ry="2" width="144" height="32" />
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
