<template>
    <content-loader
        :width="baseWidth"
        :style="{ 'transform': `scaleX(${contentWidth / baseWidth})` }"
        :height="810"
        :speed="loadingConf.speed"
        :primaryColor="loadingConf.primaryColor"
        :secondaryColor="loadingConf.secondaryColor">
        <rect x="19" y="137" rx="1" ry="1" width="73" height="16" /> 
        <rect x="19" y="241" rx="1" ry="1" width="170" height="16" /> 
        <rect x="116" y="136" rx="1" ry="1" width="64" height="17" /> 
        <rect x="206" y="136" rx="1" ry="1" width="64" height="16" /> 
        <path d="M 0 167 h 1180 v 1 H 0 z M 0 331 h 1180 v 1 H 0 z" /> 
        <rect x="335" y="354" rx="2" ry="2" width="880" height="447" /> 
        <rect x="0" y="0" rx="2" ry="2" width="1180" height="106" /> 
        <rect x="19" y="189" rx="2" ry="2" width="1140" height="38" /> 
        <rect x="19" y="266" rx="2" ry="2" width="560" height="42" /> 
        <rect x="599" y="266" rx="2" ry="2" width="560" height="42" /> 
        <circle cx="32" cy="379" r="8" /> 
        <circle cx="32" cy="539" r="8" /> 
        <circle cx="32" cy="699" r="8" /> 
        <circle cx="32" cy="416" r="5" /> 
        <circle cx="31" cy="576" r="5" /> 
        <circle cx="31" cy="616" r="5" /> 
        <circle cx="31" cy="736" r="5" /> 
        <circle cx="31" cy="776" r="5" /> 
        <circle cx="31" cy="656" r="5" /> 
        <circle cx="32" cy="456" r="5" /> 
        <circle cx="32" cy="496" r="5" /> 
        <path d="M 30.5 384.781 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 v 3 h 1 v -3 h -1 z m 0 6 V 771 h 1 v -2.219 h -1 z" /> 
        <rect x="44" y="371" rx="2" ry="2" width="56" height="16" /> 
        <rect x="44" y="531" rx="2" ry="2" width="56" height="16" /> 
        <rect x="44" y="691" rx="2" ry="2" width="56" height="16" /> 
        <rect x="44" y="729" rx="2" ry="2" width="113" height="16" /> 
        <rect x="44" y="769" rx="2" ry="2" width="113" height="16" /> 
        <rect x="44" y="569" rx="2" ry="2" width="113" height="16" /> 
        <rect x="44" y="609" rx="2" ry="2" width="113" height="16" /> 
        <rect x="44" y="649" rx="2" ry="2" width="113" height="16" /> 
        <rect x="44" y="409" rx="2" ry="2" width="113" height="16" /> 
        <rect x="44" y="449" rx="2" ry="2" width="113" height="16" /> 
        <rect x="44" y="489" rx="2" ry="2" width="113" height="16" />
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
