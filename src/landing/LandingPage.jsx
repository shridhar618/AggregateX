import { useState } from 'react'
import { Faq, FinalCta, Footer } from './Closing'
import EditorShowcase from './EditorShowcase'
import { EngineProvider } from './engine'
import Hero from './Hero'
import IntroLoader from './IntroLoader'
import LandingNav from './LandingNav'
import LiveDemo from './LiveDemo'
import { IntroContext, shouldSkipIntro } from './motion'
import Pricing from './Pricing'
import { Band, Features, Statement, Workflow } from './Sections'
import { Capabilities, Privacy } from './Trust'
import './landing.css'

export default function LandingPage() {
  const [skip] = useState(shouldSkipIntro)
  const [ready, setReady] = useState(skip)

  return (
    <EngineProvider>
      <IntroContext.Provider value={ready}>
        <div className="lp">
          {!skip && <IntroLoader onDone={() => setReady(true)} />}
          <a href="#main" className="lp-skip">Skip to content</a>
          <LandingNav />
          <main id="main">
            <Hero />
            <Statement />
            <Band />
            <LiveDemo />
            <Features />
            <Workflow />
            <EditorShowcase />
            <Privacy />
            <Capabilities />
            <Pricing />
            <Faq />
            <FinalCta />
          </main>
          <Footer />
        </div>
      </IntroContext.Provider>
    </EngineProvider>
  )
}
