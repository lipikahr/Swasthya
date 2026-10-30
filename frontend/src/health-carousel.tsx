import { useEffect, useMemo, useState, type KeyboardEvent } from "react";
import { Outlet } from "react-router-dom";
import { HEALTH_SLIDES, type HealthSlide } from "./health-slides";

const INTERVAL_MS = 6000;

export function HealthCarousel({
  slides = HEALTH_SLIDES,
  intervalMs = INTERVAL_MS,
}: {
  slides?: HealthSlide[];
  intervalMs?: number;
}) {
  const [index, setIndex] = useState(0);
  const [hidden, setHidden] = useState(false);
  const [failed, setFailed] = useState<Set<string>>(() => new Set());

  const live = useMemo(() => slides.filter((slide) => !failed.has(slide.id)), [slides, failed]);

  useEffect(() => {
    slides.forEach((slide) => {
      const image = new Image();
      image.src = slide.src;
    });
  }, [slides]);

  useEffect(() => {
    const sync = () => setHidden(document.hidden);
    sync();
    document.addEventListener("visibilitychange", sync);
    return () => document.removeEventListener("visibilitychange", sync);
  }, []);

  useEffect(() => {
    if (live.length === 0) {
      setIndex(0);
      return;
    }
    if (index >= live.length) setIndex(0);
  }, [index, live.length]);

  useEffect(() => {
    if (hidden || live.length < 2) return;
    const timer = window.setInterval(() => {
      setIndex((current) => (current + 1) % live.length);
    }, intervalMs);
    return () => window.clearInterval(timer);
  }, [hidden, live.length, intervalMs]);

  function go(step: number) {
    if (live.length < 2) return;
    setIndex((current) => (current + step + live.length) % live.length);
  }

  function onError(id: string) {
    setFailed((current) => {
      if (current.has(id)) return current;
      const next = new Set(current);
      next.add(id);
      return next;
    });
  }

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      go(-1);
    }
    if (event.key === "ArrowRight") {
      event.preventDefault();
      go(1);
    }
  }

  const active = live[index];

  return (
    <div
      className={`health-carousel${live.length === 0 ? " is-empty" : ""}`}
      role="region"
      aria-roledescription="carousel"
      aria-label="Health and nutrition images"
    >
      <div className="health-carousel-slides">
        {slides.map((slide) => (
          <img
            key={slide.id}
            src={slide.src}
            alt=""
            className={slide.id === active?.id ? "is-active" : undefined}
            draggable={false}
            decoding="async"
            onError={() => onError(slide.id)}
          />
        ))}
      </div>
      {live.length > 1 ? (
        <div className="health-carousel-controls" onKeyDown={onKeyDown}>
          <button type="button" className="health-carousel-btn" aria-label="Previous image" onClick={() => go(-1)}>
            ‹
          </button>
          <div className="health-carousel-dots">
            {live.map((slide, slideIndex) => (
              <button
                key={slide.id}
                type="button"
                aria-label={slide.alt}
                aria-current={slideIndex === index ? "true" : undefined}
                onClick={() => setIndex(slideIndex)}
              />
            ))}
          </div>
          <button type="button" className="health-carousel-btn" aria-label="Next image" onClick={() => go(1)}>
            ›
          </button>
        </div>
      ) : null}
    </div>
  );
}

export function AuthLayout() {
  return (
    <div className="auth-stage">
      <Outlet />
    </div>
  );
}
