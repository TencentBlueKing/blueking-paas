<template>
    <content-loader
        :width="baseWidth"
        :style="{ 'transform': `scaleX(${contentWidth / baseWidth})` }"
        :height="1012"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor">
        <rect x="0" y="806" rx="2" ry="2" width="568" height="180" /> 
        <rect x="612" y="806" rx="2" ry="2" width="568" height="180" /> 
        <rect x="1" y="276" rx="2" ry="2" width="144" height="32" /> 
        <rect x="1" y="503" rx="2" ry="2" width="144" height="32" /> 
        <rect x="0" y="58" rx="2" ry="2" :width="baseWidth" height="40" /> 
        <rect x="0" y="397" rx="2" ry="2" :width="baseWidth" height="42" /> 
        <rect x="0" y="624" rx="2" ry="2" :width="baseWidth" height="42" /> 
        <rect x="0" y="102" rx="2" ry="2" :width="baseWidth" height="40" /> 
        <rect x="0" y="449" rx="2" ry="2" :width="baseWidth" height="42" /> 
        <rect x="0" y="676" rx="2" ry="2" :width="baseWidth" height="42" /> 
        <rect x="0" y="146" rx="2" ry="2" :width="baseWidth" height="40" /> 
        <rect x="1" y="0" rx="1" ry="1" width="100" height="20" /> 
        <rect x="1" y="566" rx="1" ry="1" width="100" height="20" /> 
        <rect x="1" y="748" rx="1" ry="1" width="100" height="20" /> 
        <rect x="1" y="339" rx="1" ry="1" width="100" height="20" /> 
        <rect x="1" y="214" rx="1" ry="1" width="100" height="20" /> 
        <rect x="1" y="24" rx="1" ry="1" width="340" height="16" /> 
        <rect x="1" y="590" rx="1" ry="1" width="340" height="16" /> 
        <rect x="1" y="772" rx="1" ry="1" width="820" height="16" /> 
        <rect x="1" y="996" rx="1" ry="1" width="567" height="16" /> 
        <rect x="1" y="363" rx="1" ry="1" width="340" height="16" /> 
        <rect x="1" y="238" rx="1" ry="1" width="340" height="16" />
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
