<template>
  <div class="home">
    <div class="home__glow home__glow--one" />
    <div class="home__glow home__glow--two" />
    <div class="home__glow home__glow--three" />
    <h1>Hello, This is demo page.</h1>
  </div>
</template>

<style scoped>
.home {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  width: 100%;
  min-width: 0;
  min-height: 100vh;
  min-height: 100dvh;
  background:
    radial-gradient(1200px 600px at 12% -10%, rgba(255, 255, 255, 0.8), transparent 55%),
    radial-gradient(900px 500px at 88% 110%, rgba(58, 132, 255, 0.16), transparent 50%),
    linear-gradient(160deg, #f4f9ff 0%, #d7e9ff 48%, #c5e0ff 100%);
}

.home__glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(8px);
  pointer-events: none;
}

.home__glow--one {
  top: 18%;
  left: 16%;
  width: 180px;
  height: 180px;
  background: rgba(105, 157, 244, 0.18);
}

.home__glow--two {
  right: 14%;
  bottom: 16%;
  width: 240px;
  height: 240px;
  background: rgba(58, 132, 255, 0.14);
}

.home__glow--three {
  top: 42%;
  left: 52%;
  width: 90px;
  height: 90px;
  background: rgba(255, 255, 255, 0.55);
}

h1 {
  position: relative;
  margin: 0;
  padding: 0 24px;
  color: #1e4f8c;
  font-size: clamp(28px, 5vw, 52px);
  font-weight: 600;
  letter-spacing: 0.02em;
  text-align: center;
  text-shadow: 0 8px 24px rgba(58, 132, 255, 0.16);
}
</style>
