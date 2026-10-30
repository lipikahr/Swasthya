import { useRef } from "react";
import { Link } from "react-router-dom";
import "lenis/dist/lenis.css";
import { useLandingMotion } from "./landing/use-landing-motion";
import { useSession } from "./session";
import "./landing/landing.css";

const STEPS = [
  ["01", "Describe your meal", "Tell Swasthya what you ate and how much, in everyday language."],
  ["02", "Identify your food", "We match your description to foods in the verified nutrition dataset and ask a follow-up when an important detail is unclear."],
  ["03", "Review before saving", "Check the food, quantity, nutrition information, and breakfast, lunch, snack, or dinner before you confirm."],
  ["04", "Track your intake", "Confirmed meals contribute to your daily totals and to the daily, weekly, and monthly progress views."],
] as const;

const FOUNDATIONS = [
  ["Food understanding", "A sentence, a voice note, or a photo starts as a description. Swasthya asks when the food or the amount is unclear.", "/images/health-carousel/02-ingredients.jpg", "Rice, tomatoes, spinach, and a glass of water prepared for a meal"],
  ["Verified nutrition", "Nutrients are calculated from the verified dataset for a matched food and quantity. Missing values stay unknown.", "/images/health-carousel/03-balanced-plate.jpg", "A balanced plate of rice, dal, and greens"],
  ["Personal goals", "Targets follow the profile you save. A suggestion is stored only when you accept it.", "/images/health-carousel/04-body-measurements.jpg", "A weighing scale, measuring tape, and notebook on a linen table"],
  ["Progress tracking", "Today, the week, and the month compare saved meals with your calorie target. A day with no meals is no data, not a miss.", "/landing/plate.jpg", "A plate of rice, dal, and vegetables"],
] as const;

const JOURNEY = [
  ["Today", "See the meals you have already confirmed, grouped by breakfast, lunch, snack, and dinner. Plans and drafts are not counted.", "Saved meals only", "/landing/plate.jpg", "A plate of rice, dal, and vegetables"],
  ["Plan", "Generate a food plan for a date. Nothing in that plan is eaten until you confirm it in Coach.", "A plan is not a meal", "/images/health-carousel/02-ingredients.jpg", "Rice, tomatoes, spinach, and a glass of water prepared for a meal"],
  ["Coach", "Describe the food in text, by voice, or with a photo. A photo returns candidates. Nutrition is still calculated only after you confirm.", "Confirm before it counts", "/images/health-carousel/01-healthy-meal.jpg", "Idlis with sambar and coconut chutney"],
  ["Diary", "Move through the week and open a day. Only confirmed meals appear, with the foods and quantities that were saved.", "The record of the day", "/images/health-carousel/06-fitness-walk.jpg", "A person walking along a quiet tree-lined path"],
] as const;

const MOMENTS = [
  ["Allergy-aware choices", "Declared allergies are matched against food names. That is not a claim that a meal is allergy-safe.", "/landing/features/allergy.jpg", "Fresh vegetables and legumes arranged for cooking"],
  ["Personalised daily plan", "A generated day follows your diet, cuisine, and likes. You can still add breakfast, lunch, dinner, or an extra meal by hand.", "/landing/features/plan.jpg", "A planned South Indian vegetarian plate"],
  ["Weekly tracker", "Progress compares saved days with your calorie target. Days with no meals stay empty.", "/landing/features/week.jpg", "A weekly calendar beside a cup of tea"],
  ["Multilingual logging", "Describe a meal in English or another supported Indian language. The food is still matched to the verified dataset.", "/landing/features/language.jpg", "A notebook with food names in more than one script"],
] as const;

const DAY = [
  ["Describe it", "Say what you ate in everyday language.", "/landing/steps/01-describe.jpg", "Hands holding a phone beside a plate of food"],
  ["Match a food", "Swasthya looks for that food in the verified dataset.", "/landing/steps/02-match.jpg", "A mixed Indian meal with small blank cards"],
  ["Clear the gap", "If the name or amount is ambiguous, it asks before anything is stored.", "/landing/steps/03-clarify.jpg", "A bowl with a measuring cup and spoon"],
  ["Read the nutrients", "Energy, protein, carbohydrate, fat, and fibre come from the dataset for that quantity.", "/landing/steps/04-nutrients.jpg", "A measured portion of food beside a kitchen scale"],
  ["Choose the meal", "Mark it as breakfast, lunch, snack, or dinner.", "/landing/steps/05-meal.jpg", "Four small plates arranged from morning to night"],
  ["Confirm", "The meal is saved only after you confirm. A suggestion is not an eaten meal.", "/landing/steps/06-confirm.jpg", "A finger tapping a tick on a phone beside a plate"],
  ["See it later", "Confirmed meals appear in Today, Diary, and Progress.", "/landing/steps/07-diary.jpg", "An open journal and calendar with tea"],
] as const;

const LEDGER = [
  ["Matched food and quantity", "Nutrition is calculated for the food and amount you confirm."],
  ["Unknown stays unknown", "If the dataset has no value, Swasthya does not fill one in."],
  ["A follow-up, not a guess", "An unclear food or amount is a question, not a saved fact."],
  ["Your own foods", "Foods you add stay in your library. They are not written into the verified catalogue."],
  ["Allergies", "Declared allergies are matched against food names. That is not a claim that a meal is allergy-safe."],
] as const;

const QUESTIONS = [
  ["Is a plan counted as eaten?", "No. A plan stays a plan until you confirm those foods as a meal in Coach."],
  ["Can the assistant invent nutrition?", "No. Nutrient values come from the verified dataset, or from nutrition you supplied for a food in your library."],
  ["What if a food or amount is unclear?", "Swasthya asks a follow-up. Nothing is stored until the food, the quantity, and the meal type are confirmed."],
  ["Do voice and photos save a meal by themselves?", "No. Voice becomes text you can edit. A photo suggests food candidates. You still confirm the meal before it is saved."],
  ["What does an empty day mean?", "A day with no saved meals is no data, not a missed goal. Intake above your calorie band is not treated as success."],
  ["Do I need an account?", "Yes. Logging, plans, the diary, and progress are available after you register and sign in."],
] as const;

export function LandingPage() {
  const rootRef = useRef<HTMLElement>(null);
  const { user } = useSession();
  useLandingMotion(rootRef);
  const primary = user ? { to: "/log", label: "Log a Meal" } : { to: "/register", label: "Create an account" };
  const secondary = user ? { to: "/progress", label: "Explore Your Progress" } : { to: "/login", label: "Login" };

  return (
    <article className="lp" ref={rootRef}>
      <section id="opening" className="lp-opening" aria-labelledby="opening-heading">
        <div className="lp-first">
          <div className="lp-intro">
            <p className="script">Your personal nutrition companion</p>
            <h1 id="opening-heading">Build healthier habits, one meal at a time.</h1>
            <p className="lede">Understand what you eat, keep track of your nutrition, and see how your everyday choices add up.</p>
            <div className="row-actions">
              <Link className="button" to="/log">Log a Meal</Link>
              <Link className="soft" to={user ? "/progress" : "/register"}>{user ? "Explore Your Progress" : "Create an account"}</Link>
            </div>
          </div>
          <div className="lp-shapes" aria-hidden="true">
            <span className="lp-shape lp-arch"><i /></span>
            <span className="lp-shape lp-circle"><i /></span>
            <span className="lp-shape lp-plus"><i /></span>
            <span className="lp-shape lp-diamond"><i /></span>
          </div>
          <figure className="lp-photo">
            <div className="lp-photo-in">
              <img src="/images/health-carousel/01-healthy-meal.jpg" alt="Idlis with sambar and coconut chutney" />
            </div>
          </figure>
        </div>
        <div className="lp-second">
          <div className="lp-door" aria-hidden="true" />
          <div className="lp-visit">
            <h2 className="lp-visit-title" data-rise>Four steps from a spoken meal to a saved record.</h2>
            <ol className="lp-steps">
              {STEPS.map(([number, title, copy]) => (
                <li key={number} className="lp-step">
                  <div className="lp-step-top">
                    <span>{number}</span>
                    <span className={`lp-mark${number === "02" ? " is-square" : ""}${number === "03" ? " is-arch" : ""}${number === "04" ? " is-diamond" : ""}`} aria-hidden="true" />
                  </div>
                  <h3>{title}</h3>
                  <p>{copy}</p>
                </li>
              ))}
            </ol>
          </div>
        </div>
      </section>

      <section id="how" className="lp-wrap lp-doors" aria-labelledby="doors-heading">
        <figure className="lp-door-photo">
          <div className="lp-door-frame">
            <div className="lp-mock">
              <div className="lp-mock-bubble">
                <p className="eyebrow">You</p>
                <p>“I had two idlis and a bowl of sambar for breakfast.”</p>
                <p className="muted">Illustrative example, not a saved meal.</p>
              </div>
            </div>
          </div>
          <figcaption>Say it your way</figcaption>
        </figure>
        <div className="lp-doors-copy">
          <p className="eyebrow">Nutrition assistant</p>
          <h2 id="doors-heading" data-rise>Describe the meal. Confirm it. Then it counts.</h2>
          <p className="muted">Type, speak, or send a photo. Swasthya matches the food, then waits for you.</p>
          <div className="lp-side-list">
            <div>
              <h3>Say it your way</h3>
              <p className="muted">Type, speak, or send a photo, in English or your own language.</p>
            </div>
            <div>
              <h3>Swasthya checks the details</h3>
              <p className="muted">If a dish has several versions or the amount is missing, it asks before anything is saved.</p>
            </div>
            <div>
              <h3>You confirm, then it counts</h3>
              <p className="muted">You review the food, amount, and meal. Only then is it saved, using verified dataset values.</p>
            </div>
          </div>
        </div>
        <figure className="lp-door-photo">
          <div className="lp-door-frame">
            <div className="lp-mock">
              <div className="lp-mock-card">
                <p className="eyebrow">Check this meal</p>
                <p>Idli · 2 piece</p>
                <p>Sambar · 1 bowl</p>
                <p><span className="lp-mock-chip">Breakfast</span></p>
                <p className="lp-mock-button">Confirm & Log</p>
                <p className="muted">Illustrative example. No sample calorie count.</p>
              </div>
            </div>
          </div>
          <figcaption>Confirm what counts</figcaption>
        </figure>
      </section>

      <section id="foundations" className="lp-band" aria-labelledby="foundations-heading">
        <div className="lp-wrap lp-head">
          <p className="eyebrow">Foundations</p>
          <h2 id="foundations-heading" data-rise>What Swasthya is built on.</h2>
          <p className="muted">Four ideas sit under the product: understand the food, use verified numbers, keep your own goals, and read progress from saved meals.</p>
        </div>
        <div className="lp-deal-stage" style={{ position: "relative" }}>
          <ul className="lp-deal">
            {FOUNDATIONS.map(([title, copy, src, alt]) => (
              <li key={title} className="lp-panel">
                <img src={src} alt={alt} />
                <h3>{title}</h3>
                <p>{copy}</p>
              </li>
            ))}
          </ul>
          <span className="lp-drift lp-drift-a" data-drift="1" aria-hidden="true" />
          <span className="lp-drift lp-drift-b" data-drift="-1" aria-hidden="true" />
        </div>
      </section>

      <section id="journey" className="lp-wrap lp-band" aria-labelledby="journey-heading">
        <div className="lp-head">
          <p className="eyebrow">A day with Swasthya</p>
          <h2 id="journey-heading" data-rise>Move through the day in four places.</h2>
          <p className="muted">Today, Plan, Coach, and Diary are separate. Only a confirmed meal changes what you have eaten.</p>
        </div>
        <ol className="lp-journey">
          {JOURNEY.map(([title, copy, note, src, alt]) => (
            <li key={title} className="lp-journey-row">
              <span className="lp-rule" aria-hidden="true" />
              <div className="lp-journey-frame"><img src={src} alt={alt} /></div>
              <div>
                <h3>{title}</h3>
                <p className="muted">{copy}</p>
              </div>
              <p className="lp-note">{note}</p>
            </li>
          ))}
        </ol>
      </section>

      <section id="meals" className="lp-wrap lp-band" aria-labelledby="meals-heading">
        <div className="lp-head">
          <p className="eyebrow">More than a food log</p>
          <h2 id="meals-heading" data-rise>Allergy-aware choices, a daily plan, a weekly tracker, and your own language.</h2>
          <p className="muted">Allergy matching is by food name. A plan follows the diet and cuisine you save. Progress reads only confirmed meals. Logging works in supported Indian languages.</p>
        </div>
        <div className="lp-meals">
          {MOMENTS.map(([title, copy, src, alt], index) => (
            <article key={title} className="lp-meal">
              <div className="lp-meal-frame" data-reshape={index === 0 ? "circle" : index === 1 ? "arch" : index === 2 ? "square" : "diamond"}>
                <img src={src} alt={alt} />
              </div>
              <h3>{title}</h3>
              <p className="muted">{copy}</p>
            </article>
          ))}
        </div>
      </section>

      <section id="day" className="lp-band" aria-labelledby="day-heading">
        <div className="lp-pin">
          <div className="lp-wrap lp-head" style={{ textAlign: "left", justifyItems: "start" }}>
            <h2 id="day-heading">From the table to the diary.</h2>
            <p className="muted">Seven steps, in order. None of them is a result until you confirm the meal.</p>
          </div>
          <div className="lp-track-viewport">
            <ul className="lp-track">
              {DAY.map(([title, copy, src, alt]) => (
                <li key={title} className="lp-card">
                  <div className="lp-card-frame"><img src={src} alt={alt} /></div>
                  <h3>{title}</h3>
                  <p className="muted">{copy}</p>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      <section id="nutrition" aria-labelledby="nutrition-heading">
        <div className="lp-wrap lp-verified">
          <div>
            <p className="eyebrow">Verified data</p>
            <h2 id="nutrition-heading" data-rise>We calculate what the dataset supports.</h2>
            <p>This page does not show a sample calorie count. A real figure appears only on the meal you are about to save, or in Today after it is saved.</p>
          </div>
          <div className="lp-ledger">
            {LEDGER.map(([title, copy]) => (
              <div key={title}>
                <h3>{title}</h3>
                <p className="muted">{copy}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="story" className="lp-wrap lp-story" aria-labelledby="story-heading">
        <div className="lp-story-stage">
          <figure className="lp-story-frame">
            <img src="/landing/story-day.jpg" alt="A tall view of a home-cooked Indian plate filling the day" />
          </figure>
        </div>
        <div className="lp-story-copy">
          <h2 id="story-heading" data-rise>Everyday meals become a clear picture of your day.</h2>
          <article className="lp-beat">
            <h3>One plate</h3>
            <p className="muted">A photograph can help name the food. It does not become a saved meal by itself.</p>
          </article>
          <article className="lp-beat">
            <h3>A few words</h3>
            <p className="muted">“One chapati at lunch” is the kind of sentence Coach can resolve. The energy value is shown when that food and quantity are confirmed, not here.</p>
          </article>
          <article className="lp-beat">
            <h3>The day beside your target</h3>
            <p className="muted">Progress compares saved intake with the calorie target you set. Days without saved meals stay empty.</p>
          </article>
        </div>
      </section>

      <section id="questions" className="lp-wrap lp-faq" aria-labelledby="questions-heading">
        <div>
          <p className="eyebrow">Questions</p>
          <h2 id="questions-heading" data-rise>Before you log a meal.</h2>
        </div>
        <div>
          {QUESTIONS.map(([question, answer]) => (
            <details key={question}>
              <summary>{question}</summary>
              <p className="muted">{answer}</p>
            </details>
          ))}
        </div>
      </section>

      <section id="start" className="lp-close" aria-labelledby="start-heading">
        <div className="lp-close-panel">
          <div className="stack">
            <p className="script">Good food, honestly recorded</p>
            <h2 id="start-heading" data-rise>Start with the meal in front of you.</h2>
            <p>Set your profile, log what you eat, and follow progress from verified nutrition.</p>
            <div className="row-actions">
              <Link className="button" to={primary.to}>{primary.label}</Link>
              <Link className="soft" to={secondary.to}>{secondary.label}</Link>
            </div>
          </div>
          <div className="lp-close-photo" data-reshape="arch">
            <img src="/landing/ingredients.jpg" alt="Fresh vegetables, grains, and herbs arranged for cooking" />
          </div>
        </div>
      </section>
    </article>
  );
}
