"use client";

import Link from "next/link";

/**
 * Marketing home only — Ask lives at /ask so the first screen isn’t a chat app.
 */
export default function HomePage() {
  return (
    <main className="home">
      <section className="hero-bleed" aria-label="KitchenLab">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          className="hero-bleed-media"
          src="/images/hero.jpg"
          alt="Fresh ingredients and prepared dishes"
        />
        <div className="hero-bleed-scrim" aria-hidden />
        <div className="hero-bleed-content">
          <p className="brand">KitchenLab</p>
          <h1 className="tagline">Cook better through science.</h1>
          <p className="lede">
            Grounded answers and science-annotated recipes — not chatbot
            guesswork.
          </p>
          <div className="hero-cta">
            <Link href="/ask" className="btn">
              Start asking
            </Link>
            <Link href="/recipes" className="btn btn-ghost">
              Browse recipes
            </Link>
          </div>
        </div>
      </section>

      <section className="home-band" aria-labelledby="trust-heading">
        <div className="home-rail home-split">
          <div className="home-split-copy">
            <h2 id="trust-heading" className="section-heading">
              Built like a kitchen with stations
            </h2>
            <p className="section-lede">
              Ask for quick help. Recipes for full dishes with Why + Science on
              every step. Lab to practice. Calculators when you need exact
              numbers. Your kitchen profile personalizes the rest.
            </p>
            <ul className="home-feature-list">
              <li>
                <Link href="/ask">
                  <strong>Ask</strong>
                  <span>Questions, diagnoses, substitutions</span>
                </Link>
              </li>
              <li>
                <Link href="/recipes">
                  <strong>Recipes</strong>
                  <span>Generate &amp; save science-backed dishes</span>
                </Link>
              </li>
              <li>
                <Link href="/lab">
                  <strong>Lab</strong>
                  <span>Techniques, experiments, notebook</span>
                </Link>
              </li>
              <li>
                <Link href="/calculators">
                  <strong>Calculators</strong>
                  <span>Brine, scale, baker’s %, grams</span>
                </Link>
              </li>
            </ul>
          </div>
          <figure className="home-split-media">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/images/pasta.jpg"
              alt="Plate of pasta with tomato sauce"
            />
          </figure>
        </div>
      </section>

      <section className="home-band home-band--soft" aria-labelledby="promise-heading">
        <div className="home-rail home-promise">
          <figure className="home-promise-media">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/images/bread.jpg" alt="Fresh bread and grains" />
          </figure>
          <div className="home-promise-copy">
            <h2 id="promise-heading" className="section-heading">
              Numbers you can trust
            </h2>
            <p className="section-lede">
              Safety temps and math come from code and a cited knowledge base.
              The AI explains — it doesn’t invent critical facts.
            </p>
            <Link href="/ask" className="btn">
              Ask your first question
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}
