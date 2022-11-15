<template>
  <deploy-action
    :environment="'stag'"
  />
</template>

<script>
    import deployAction from './comps/deploy-action';

    export default {
        components: {
            deployAction
        },
        props: {
            moduleId: {
                type: String,
                default: ''
            }
        }
    };
</script>
