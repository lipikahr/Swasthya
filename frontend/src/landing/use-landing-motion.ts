import { useLayoutEffect, type RefObject } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { SplitText } from "gsap/SplitText";
import Lenis from "lenis";

gsap.registerPlugin(ScrollTrigger, SplitText);

function offsetWithin(element: HTMLElement, root: HTMLElement) {
  let x = 0;
  let y = 0;
  let node: HTMLElement | null = element;
  while (node && node !== root) {
    x += node.offsetLeft;
    y += node.offsetTop;
    node = node.offsetParent as HTMLElement | null;
  }
  return { x, y };
}

export function useLandingMotion(rootRef: RefObject<HTMLElement | null>) {
  useLayoutEffect(() => {
    const root = rootRef.current;
    if (!root) return;

    const nav = document.querySelector<HTMLElement>(".topbar");
    const setNavHeight = () => {
      document.documentElement.style.setProperty("--nav-h", `${nav?.offsetHeight ?? 92}px`);
    };
    setNavHeight();

    const mm = gsap.matchMedia();

    mm.add("(prefers-reduced-motion: no-preference)", () => {
      const lenis = new Lenis({
        lerp: 0.09,
        wheelMultiplier: 0.95,
        anchors: { offset: -(nav?.offsetHeight ?? 92) },
      });
      const tick = (time: number) => lenis.raf(time * 1000);
      lenis.on("scroll", ScrollTrigger.update);
      gsap.ticker.add(tick);
      gsap.ticker.lagSmoothing(0);

      root.querySelectorAll<HTMLElement>("[data-rise]").forEach((element) => {
        const split = SplitText.create(element, { type: "lines", mask: "lines", linesClass: "lp-rise-line" });
        const timeline = gsap.timeline({ paused: true, onComplete: () => split.revert() });
        timeline.from(split.lines, { yPercent: 105, duration: 0.95, ease: "power3.out", stagger: 0.09 });
        ScrollTrigger.create({
          trigger: element,
          start: "top 88%",
          once: true,
          onEnter: () => timeline.play(),
        });
      });

      root.querySelectorAll<HTMLElement>("[data-reshape]").forEach((element) => {
        const from = {
          circle: "inset(9% 9% 9% 9% round 50%)",
          arch: "inset(10% 6% 0% 6% round 50% 50% 0% 0%)",
          square: "inset(14% 14% 14% 14% round 0)",
          diamond: "inset(18% 18% 18% 18% round 12%)",
        }[element.dataset.reshape || "circle"];
        const image = element.querySelector("img");
        const timeline = gsap.timeline({ paused: true, onComplete: () => gsap.set(element, { clearProps: "clipPath" }) });
        timeline
          .fromTo(element, { clipPath: from }, { clipPath: "inset(0% round 0)", duration: 1.15, ease: "power3.inOut" }, 0)
          .from(image, { scale: 1.22, duration: 1.4, ease: "power3.out" }, 0);
        ScrollTrigger.create({
          trigger: element,
          start: "top 86%",
          once: true,
          onEnter: () => timeline.play(),
        });
      });

      root.querySelectorAll<HTMLElement>("[data-drift]").forEach((element) => {
        const direction = Number(element.dataset.drift || 1);
        ScrollTrigger.create({
          trigger: element,
          start: "top bottom",
          end: "bottom top",
          scrub: 0.8,
          animation: gsap.timeline()
            .fromTo(element, { y: 70 * direction, rotation: -40 * direction }, { y: 0, rotation: 0, ease: "power1.out", duration: 0.42 })
            .to(element, { y: 0, duration: 0.16 })
            .to(element, { y: -70 * direction, rotation: 40 * direction, ease: "power1.in", duration: 0.42 }),
        });
      });

      const section = root.querySelector<HTMLElement>("#opening");
      const arch = section?.querySelector<HTMLElement>(".lp-arch");
      const door = section?.querySelector<HTMLElement>(".lp-door");
      const second = section?.querySelector<HTMLElement>(".lp-second");
      const photo = section?.querySelector<HTMLElement>(".lp-photo");
      const title = section?.querySelector<HTMLElement>(".lp-visit-title");
      const marks = section?.querySelectorAll<HTMLElement>(".lp-mark") ?? [];
      const others = section ? [...section.querySelectorAll<HTMLElement>(".lp-shape:not(.lp-arch)")] : [];
      if (section && arch && door && second && photo && title) {
        let geometry = { x: 0, y: 0, sx: 1, sy: 1 };
        const measure = () => {
          const a = offsetWithin(arch, section);
          const d = offsetWithin(door, section);
          geometry = {
            x: d.x - a.x,
            y: d.y - a.y,
            sx: door.offsetWidth / arch.offsetWidth,
            sy: door.offsetHeight / arch.offsetHeight,
          };
        };
        measure();
        gsap.set(arch, { transformOrigin: "0 0" });
        gsap.set(door, { autoAlpha: 0 });
        const flung = [[-260, -120, -150], [240, 160, 140], [-200, 220, 120], [220, 260, -110]];
        const timeline = gsap.timeline({
          defaults: { ease: "none" },
          scrollTrigger: {
            trigger: section,
            start: "top top",
            end: () => `+=${offsetWithin(second, section).y}`,
            scrub: 0.7,
            invalidateOnRefresh: true,
            onRefreshInit: measure,
          },
        });
        timeline
          .to(arch, { x: () => geometry.x, y: () => geometry.y, duration: 1 }, 0)
          .to(arch, { scaleX: () => geometry.sx, scaleY: () => geometry.sy, duration: 1 }, 0)
          .to(photo, { scale: 0.8, yPercent: -6, borderRadius: "160px 260px 160px 160px", duration: 0.85, ease: "power1.in" }, 0)
          .fromTo(title, { scale: 0.86, transformOrigin: "50% 100%" }, { scale: 1, duration: 0.45, ease: "power2.out" }, 0.55);
        others.forEach((shape, index) => {
          const [x, y, rotation] = flung[index] ?? [0, 0, 0];
          timeline.to(shape, { x, y, rotation, scale: 1.9, duration: 0.6, ease: "power1.out" }, 0.04 * index);
        });
        timeline
          .fromTo(marks, { scale: 0.2, rotation: -120 }, { scale: 1, rotation: 0, duration: 0.25, stagger: 0.05, ease: "back.out(2)" }, 0.7)
          .set(door, { autoAlpha: 1 }, 1)
          .set(arch, { autoAlpha: 0 }, 1);
      }

      const grid = root.querySelector<HTMLElement>(".lp-doors");
      const doors = grid ? [...grid.querySelectorAll<HTMLElement>(".lp-door-photo")] : [];
      if (grid && doors.length) {
        const shift = (doorPhoto: HTMLElement) => grid.offsetWidth / 2 - (doorPhoto.offsetLeft + doorPhoto.offsetWidth / 2);
        const timeline = gsap.timeline({
          defaults: { ease: "none" },
          scrollTrigger: { trigger: grid, start: "top 82%", end: "top 22%", scrub: 0.6, invalidateOnRefresh: true },
        });
        doors.forEach((doorPhoto, index) => {
          const side = index ? 1 : -1;
          timeline
            .fromTo(doorPhoto, { x: () => shift(doorPhoto) * 0.92 }, { x: 0, duration: 1, ease: "power2.inOut" }, 0)
            .fromTo(doorPhoto.querySelector(".lp-door-frame"), { clipPath: "inset(0% 30% 0% 30% round 999px 999px 0 0)" }, { clipPath: "inset(0% round 0)", duration: 1, ease: "power2.inOut" }, 0)
            .fromTo(doorPhoto.querySelector(".lp-door-frame > *"), { xPercent: -14 * side, scale: 1.18 }, { xPercent: 0, scale: 1, duration: 1, ease: "power1.out" }, 0);
        });
      }

      const row = root.querySelector<HTMLElement>(".lp-deal");
      const panels = row ? [...row.querySelectorAll<HTMLElement>(".lp-panel")] : [];
      if (row && panels.length) {
        const toCentre = (panel: HTMLElement, axis: "x" | "y") => axis === "x"
          ? row.offsetWidth / 2 - (panel.offsetLeft + panel.offsetWidth / 2)
          : row.offsetHeight / 2 - (panel.offsetTop + panel.offsetHeight / 2);
        const turns = [-9, 6, -4, 11];
        const timeline = gsap.timeline({
          scrollTrigger: { trigger: row, start: "top 85%", end: "bottom 60%", scrub: 0.7, invalidateOnRefresh: true },
        });
        panels.forEach((panel, index) => {
          timeline.fromTo(panel,
            { x: () => toCentre(panel, "x"), y: () => toCentre(panel, "y") + 30, rotation: turns[index % turns.length], scale: 0.86 },
            { x: 0, y: 0, rotation: 0, scale: 1, duration: 1, ease: "power2.out", clearProps: "transform" },
            index * 0.32);
        });
      }

      root.querySelectorAll<HTMLElement>(".lp-journey-row").forEach((journeyRow, index) => {
        const frame = journeyRow.querySelector<HTMLElement>(".lp-journey-frame");
        const image = frame?.querySelector("img");
        const rule = journeyRow.querySelector<HTMLElement>(".lp-rule");
        if (!frame || !image || !rule) return;
        const closed = "inset(38% 70% 38% 0% round 999px)";
        const open = "inset(0% round 0)";
        const accent = getComputedStyle(document.documentElement).getPropertyValue("--color-accent").trim();
        const ink = getComputedStyle(document.documentElement).getPropertyValue("--color-text").trim();
        gsap.timeline({
          scrollTrigger: { trigger: journeyRow, start: "top bottom", end: "bottom top", scrub: 0.5 },
        })
          .fromTo(frame, { clipPath: closed }, { clipPath: open, duration: 0.36, ease: "power2.inOut" }, 0)
          .fromTo(image, { scale: 1.3 }, { scale: 1, duration: 0.36, ease: "power2.out" }, 0)
          .fromTo(rule, { scaleX: 0.08 }, { scaleX: 1, backgroundColor: accent, duration: 0.36, ease: "power2.out" }, 0)
          .to(rule, { backgroundColor: ink, duration: 0.2 }, 0.62)
          .to(frame, { clipPath: closed, duration: 0.36, ease: "power2.inOut" }, 0.64)
          .to(image, { scale: 1.3, duration: 0.36, ease: "power2.in" }, 0.64);
        void index;
      });

      const storyText = root.querySelector<HTMLElement>(".lp-story-copy");
      const storyImage = root.querySelector<HTMLElement>(".lp-story-frame img");
      if (storyText && storyImage && window.matchMedia("(min-width: 900px)").matches) {
        gsap.timeline({
          scrollTrigger: { trigger: storyText, start: "top 55%", end: "bottom 75%", scrub: 0.8 },
        })
          .fromTo(storyImage, { scale: 2.2, transformOrigin: "42% 88%" }, { scale: 2.2, transformOrigin: "42% 88%", duration: 4.2 })
          .to(storyImage, { scale: 1.75, transformOrigin: "56% 30%", duration: 2, ease: "power2.inOut" })
          .to(storyImage, { scale: 1.75, duration: 1 })
          .to(storyImage, { scale: 1, transformOrigin: "50% 50%", duration: 2, ease: "power2.inOut" })
          .to(storyImage, { scale: 1, duration: 0.8 });
      }

      const closing = root.querySelector<HTMLElement>("#start");
      const panel = closing?.querySelector<HTMLElement>(".lp-close-panel");
      if (closing && panel) {
        const corner = () => (window.innerWidth < 901 ? 14 : 32);
        const rise = () => (window.innerWidth < 901 ? 150 : 300);
        gsap.timeline({
          scrollTrigger: { trigger: closing, start: "top 95%", end: "top 15%", scrub: 0.6, invalidateOnRefresh: true },
        }).fromTo(panel,
          { scale: 0.9, y: 60, borderRadius: () => `${corner()}px` },
          {
            scale: 1,
            y: 0,
            borderRadius: () => `${panel.offsetWidth / 2}px ${panel.offsetWidth / 2}px ${corner()}px ${corner()}px / ${rise()}px ${rise()}px ${corner()}px ${corner()}px`,
            ease: "power2.out",
            duration: 1,
          });
      }

      return () => {
        gsap.ticker.remove(tick);
        gsap.ticker.lagSmoothing(500, 33);
        lenis.destroy();
      };
    });

    mm.add("(prefers-reduced-motion: no-preference) and (min-width: 900px)", () => {
      const pin = root.querySelector<HTMLElement>(".lp-pin");
      const track = root.querySelector<HTMLElement>(".lp-track");
      const cards = track ? [...track.querySelectorAll<HTMLElement>(".lp-card")] : [];
      const section = root.querySelector<HTMLElement>("#day");
      if (!pin || !track || !section || cards.length === 0) return;
      section.dataset.track = "on";
      const setters = cards.map((card) => ({
        y: gsap.quickSetter(card, "y", "px"),
        r: gsap.quickSetter(card, "rotation", "deg"),
      }));
      const distance = () => Math.max(0, track.scrollWidth - document.documentElement.clientWidth);
      const wave = () => {
        const centre = window.innerWidth / 2;
        cards.forEach((card, index) => {
          const box = card.getBoundingClientRect();
          const raw = gsap.utils.clamp(-1.4, 1.4, (box.left + box.width / 2 - centre) / window.innerWidth);
          const d = Math.sign(raw) * Math.max(0, Math.abs(raw) - 0.1);
          setters[index].y(120 * d * d);
          setters[index].r(10 * d);
        });
      };
      gsap.to(track, {
        x: () => -distance(),
        ease: "none",
        onUpdate: wave,
        scrollTrigger: {
          trigger: pin,
          start: "top top",
          end: () => `+=${distance()}`,
          pin: true,
          scrub: 0.6,
          invalidateOnRefresh: true,
          anticipatePin: 1,
          onRefresh: wave,
        },
      });
      wave();
      return () => {
        delete section.dataset.track;
        gsap.set(cards, { clearProps: "transform" });
      };
    });

    const onResize = () => {
      setNavHeight();
      ScrollTrigger.refresh();
    };
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      mm.revert();
    };
  }, [rootRef]);
}
