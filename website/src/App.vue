<script setup lang="ts">
import PlatformDownload from "./PlatformDownload.vue";
defineProps<{ previewPlatform?: 'mac' | 'windows' | 'linux'; dashboardPreviewUrl?: string }>();
import { onMounted, onBeforeUnmount } from 'vue';
import { observePageScroll } from './analytics/scroll';
import CharacterSection from "./CharacterSection.vue";
import CrewSection from "./CrewSection.vue";
import HotkeySection from "./HotkeySection.vue";
import HeroShowcase from "./HeroShowcase.vue";
import DashboardShowcase from "./DashboardShowcase.vue";
import AnalyticsPreference from './AnalyticsPreference.vue';
import { websiteAnalytics } from './analytics';
let stopScroll: (() => void) | undefined;
onMounted(() => { stopScroll = observePageScroll(window, document, websiteAnalytics); });
onBeforeUnmount(() => stopScroll?.());
const source = "https://github.com/noisy/noisy-coding";
</script>

<template>
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="site-header wrap">
    <a class="brand" href="#" aria-label="Noisy Studio home">
      <svg viewBox="0 0 46 46" width="40" height="40" aria-hidden="true">
        <rect x="3" y="3" width="40" height="40" rx="11" fill="#263448" />
        <g stroke="#b8cff3" stroke-width="3.2" stroke-linecap="round">
          <path d="M14 17v12M20 11v24M26 15v16M32 19v8" />
        </g>
      </svg>
      Noisy Studio
    </a>
    <nav aria-label="Main navigation">
      <a href="#voices">Hear it</a><a href="#character">Character</a
      ><a :href="source">GitHub ↗</a>
    </nav>
    <a class="button small" href="#install" @click="websiteAnalytics.trackGetStarted('header')"
      >Download <span aria-hidden="true">↓</span></a
    >
  </header>
  <main id="main">
    <HeroShowcase><template #download><PlatformDownload :platform="previewPlatform ?? 'mac'" compact /></template></HeroShowcase>
    <section
      id="workflow"
      class="wrap workflow-summary"
      aria-label="How it works"
    >
      <p><span>01 / Hear</span> Updates without checking the terminal.</p>
      <p><span>02 / Answer</span> Give direction in your own words.</p>
      <p><span>03 / Continue</span> Keep your attention on the work.</p>
    </section>
    <CrewSection />
    <HotkeySection />
    <CharacterSection />
    <section id="dashboard" class="section wrap">
      <div class="section-heading">
        <div>
          <p class="eyebrow">A home for what you heard</p>
          <h2>Missed a moment?<br /><span>Pick up the conversation.</span></h2>
        </div>
        <p>
          The companion keeps you in the flow. The full application keeps the
          record: revisit messages, replay an answer, and adjust how you listen.
        </p>
      </div>
      <DashboardShowcase :preview-url="dashboardPreviewUrl" />
    </section>
    <section id="install" class="section install-section">
      <div class="wrap install-grid">
        <div>
          <p class="eyebrow">Make yourself heard</p>
          <h2>Your next session<br />could sound <em>different.</em></h2>
          <p class="section-intro">
            Bring voice into your coding workflow with Noisy Studio.
            Hear the progress, give direction, and keep creating.
          </p>
        </div>
        <PlatformDownload :platform="previewPlatform ?? 'mac'" />
      </div>
    </section>
    <section class="section wrap questions">
      <div>
        <p class="eyebrow">A few practical details</p>
        <h2>Good to know.</h2>
      </div>
      <div>
        <details>
          <summary>Does everything run locally?</summary>
          <p>
            The application runs on your machine. Speech processing uses an
            external voice provider; it is not an offline voice system.
          </p>
        </details>
        <details>
          <summary>Can I use more than one agent?</summary>
          <p>
            Yes. Conversations can have distinct voices and character settings.
            Agent speech is queued so replies take turns.
          </p>
        </details>
        <details>
          <summary>What can I customize?</summary>
          <p>
            Choose voices and avatar families, adjust Humor, Honesty, Verbosity,
            Talkative and Speed, and configure your microphone and speech
            controls.
          </p>
        </details>
      </div>
    </section>
  </main>
  <footer class="site-footer wrap">
    <a class="brand" href="#">Noisy Studio</a
    ><span>Your voice, in the workflow.</span
    ><a :href="source">Built in the open ↗</a
    ><!-- Storybook ships in the same Pages deployment (#121), so this is a
         relative path rather than a second domain to keep in sync. -->
    ><a href="storybook/">Storybook ↗</a>
  </footer>
  <AnalyticsPreference />
</template>
