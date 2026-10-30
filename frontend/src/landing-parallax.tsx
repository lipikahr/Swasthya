import { useLayoutEffect, useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

export function LandingParallax() {
  const rootRef = useRef<HTMLElement>(null);

  useLayoutEffect(() => {
    const root = rootRef.current;
    if (!root) return;

    const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const desktop = window.matchMedia("(min-width: 900px)");
    let context: gsap.Context | undefined;

    const setup = () => {
      context?.revert();
      context = undefined;
      if (motion.matches || !desktop.matches) return;
      context = gsap.context(() => {
        const scrub = { trigger: root, start: "top bottom", end: "bottom top", scrub: 0.6 };
        gsap.to(root.querySelector(".parallax-back"), { yPercent: -14, ease: "none", scrollTrigger: scrub });
        gsap.to(root.querySelector(".parallax-mid"), { yPercent: -8, ease: "none", scrollTrigger: scrub });
        gsap.to(root.querySelector(".parallax-front"), { yPercent: 10, ease: "none", scrollTrigger: scrub });
        gsap.to(root.querySelector(".parallax-note-a"), { yPercent: -18, ease: "none", scrollTrigger: scrub });
        gsap.to(root.querySelector(".parallax-note-b"), { yPercent: 12, ease: "none", scrollTrigger: scrub });
      }, root);
    };

    setup();
    motion.addEventListener("change", setup);
    desktop.addEventListener("change", setup);
    return () => {
      motion.removeEventListener("change", setup);
      desktop.removeEventListener("change", setup);
      context?.revert();
    };
  }, []);

  return (
    <section ref={rootRef} className="landing-band is-sage parallax-band" aria-labelledby="parallax-heading">
      <div className="band-inner parallax-scene">
        <div className="parallax-copy">
          <p className="eyebrow">From your plate to your progress</p>
          <h2 id="parallax-heading">Everyday meals become a clear picture of your day.</h2>
          <p className="muted">
            A photograph of lunch, a few words in the chat, and a saved entry on your dashboard.
            Swasthya keeps those steps connected without inventing numbers along the way.
          </p>
        </div>
        <div className="parallax-stage">
          <img className="parallax-layer parallax-back" src="/images/health-carousel/02-ingredients.jpg" alt="" />
          <img className="parallax-layer parallax-mid" src="/landing/plate.jpg" alt="A plate of rice, dal, and vegetables" />
          <img className="parallax-layer parallax-front" src="/images/health-carousel/07-hydration.jpg" alt="" />
          <aside className="parallax-note parallax-note-a">
            <p className="eyebrow">Meal entry</p>
            <p>1 chapati · lunch</p>
            <p className="muted">73 kcal in this example</p>
          </aside>
          <aside className="parallax-note parallax-note-b">
            <p className="eyebrow">Daily view</p>
            <p>Intake compared with your target</p>
            <div className="mini-bar" aria-hidden="true"><i style={{ width: "42%" }} /></div>
          </aside>
        </div>
      </div>
    </section>
  );
}
