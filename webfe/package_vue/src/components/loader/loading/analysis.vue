<template>
    <content-loader
        :width="baseWidth"
        :style="{ 'transform': `scaleX(${contentWidth / baseWidth})` }"
        :height="700"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor"
        >
        <rect x="0" y="44" rx="1" ry="1" width="301" height="16" /> 
        <rect x="0" y="0" rx="2" ry="2" width="100" height="32" /> 
        <rect x="102" y="0" rx="2" ry="2" width="100" height="32" /> 
        <rect x="919" y="0" rx="2" ry="2" width="260" height="32" /> 
        <rect x="0" y="72" rx="2" ry="2" :width="baseWidth" height="284" /> 
        <rect x="0" y="372" rx="2" ry="2" width="202" height="32" /> 
        <rect x="0" y="420" rx="2" ry="2" :width="baseWidth" height="42" /> 
        <rect x="0" y="475" rx="1" ry="1" :width="baseWidth" height="20" /> 
        <rect x="0" y="516" rx="1" ry="1" :width="baseWidth" height="20" /> 
        <rect x="0" y="557" rx="1" ry="1" :width="baseWidth" height="20" /> 
        <rect x="0" y="598" rx="1" ry="1" :width="baseWidth" height="20" /> 
        <rect x="0" y="639" rx="1" ry="1" :width="baseWidth" height="20" /> 
        <rect x="1111" y="372" rx="2" ry="2" width="68" height="32" /> 
        <rect x="0" y="680" rx="1" ry="1" :width="baseWidth" height="20" />
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
