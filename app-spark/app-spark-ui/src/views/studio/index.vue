<template>
  <StudioLayout>
    <InteractionPanel />
    <WorkspacePanel />
    <ManagementPanel />
  </StudioLayout>
</template>

<script setup lang="ts">
import InteractionPanel from '@/components/studio/interaction/index.vue';
import ManagementPanel from '@/components/studio/management/index.vue';
import WorkspacePanel from '@/components/studio/workspace/index.vue';
import StudioLayout from '@/layouts/StudioLayout.vue';
</script>
