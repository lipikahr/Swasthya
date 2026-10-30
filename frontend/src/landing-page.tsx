import { Link } from "react-router-dom";
import { HealthCarousel } from "./health-carousel";
import { LandingParallax } from "./landing-parallax";
import { useSession } from "./session";

const WORKFLOW = [
  ["01", "Describe your meal", "Tell Swasthya what you ate and how much, in everyday language."],
  ["02", "Identify your food", "We match your description to foods in the verified nutrition dataset and ask a follow-up when an important detail is unclear."],
  ["03", "Review before saving", "Check the food, quantity, nutrition information, and breakfast, lunch, or dinner before you confirm."],
  ["04", "Track your intake", "Confirmed meals contribute to your daily totals and to the daily, weekly, and monthly progress views."],
] as const;

const FEATURES = [
  ["Personal targets", "Targets follow the profile you save. A suggested set of numbers is stored only when you accept it."],
  ["Meal history", "Each confirmed meal stays in your log, with the foods and quantities that were actually saved."],
  ["Daily, weekly, monthly progress", "The dashboard compares saved intake with your active calorie target and shows days with no meals as no data, not as a miss."],
  ["Clarifying conversation", "If a food or amount is unclear, Swasthya asks before anything is stored."],
] as const;

const SAMPLE_WEEK = [0, 72, 48, 0, 91, 64, 0] as const;

export function LandingPage() {
  const { user } = useSession();
  const secondary = user ? { to: "/progress", label: "Explore Your Progress" } : { to: "/register", label: "Create an account" };

  return (
    <div className="landing">
      <section className="hero hero-editorial">
        <div className="hero-copy stack">
          <p className="script">Your personal nutrition companion</p>
          <h1>Build healthier habits, one meal at a time.</h1>
          <p className="lede">Understand what you eat, keep track of your nutrition, and see how your everyday choices add up.</p>
          <div className="row-actions">
            <Link className="button" to="/log">Log a Meal</Link>
            <Link className="soft" to={secondary.to}>{secondary.label}</Link>
          </div>
        </div>
        <div className="hero-stage">
          <figure className="hero-figure">
            <HealthCarousel />
            <figcaption className="hero-label">Meals, ingredients, and simple tracking</figcaption>
          </figure>
          <figure className="hero-inset hero-inset-a">
            <img src="/landing/ingredients.jpg" alt="Fresh vegetables, grains, and herbs arranged for cooking" />
            <figcaption>Whole ingredients</figcaption>
          </figure>
          <figure className="hero-inset hero-inset-b">
            <img src="/images/health-carousel/05-nutrition-tracking.jpg" alt="A food journal beside fruit on a linen table" />
            <figcaption>A record of the day</figcaption>
          </figure>
        </div>
      </section>

      <section className="story-split" aria-labelledby="meals-heading">
        <figure className="story-photo">
          <img src="/landing/hero.jpg" alt="A home-cooked Indian meal served on a plate" />
        </figure>
        <div className="stack">
          <p className="eyebrow">Your meals, better understood</p>
          <h2 id="meals-heading">Record what you eat and see how each meal fits the day.</h2>
          <p className="muted">
            Start with a sentence you would say at the table. Swasthya turns that description into a food
            entry you can check, then saves it only after you confirm.
          </p>
          <aside className="example-panel" aria-label="Illustrative meal example">
            <p className="eyebrow">Example, not live data</p>
            <p className="example-line">“I ate two idlis for breakfast.”</p>
            <p className="example-arrow" aria-hidden="true">↓</p>
            <p>2 idli · breakfast · 69 kcal in this illustration</p>
            <p className="muted">Nothing is counted toward your totals until you confirm the meal.</p>
          </aside>
        </div>
      </section>

      <LandingParallax />

      <section className="workflow" aria-labelledby="works-heading">
        <div className="workflow-intro">
          <p className="eyebrow">How Swasthya works</p>
          <h2 id="works-heading">Four steps from a spoken meal to a saved record.</h2>
        </div>
        <ol className="workflow-track">
          {WORKFLOW.map(([number, title, copy]) => (
            <li key={number}>
              <span className="workflow-index">{number}</span>
              <h3>{title}</h3>
              <p className="muted">{copy}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="landing-band is-sage" aria-labelledby="verified-heading">
        <div className="band-inner story-split reverse">
          <div className="stack">
            <p className="eyebrow">Nutrition based on verified data</p>
            <h2 id="verified-heading">We calculate what the dataset supports. We do not invent the rest.</h2>
            <p className="muted">
              Swasthya uses structured nutrition data to calculate the nutrients available for a matched food
              and quantity. When information is missing, it remains unknown rather than being invented.
            </p>
            <p className="muted">
              Not every food, serving size, or conversion is available. Follow-up questions exist so a guess
              is never stored as a fact.
            </p>
          </div>
          <figure className="story-photo layered-photo">
            <img src="/images/health-carousel/03-balanced-plate.jpg" alt="A balanced plate of rice, dal, and greens" />
            <aside className="nutrition-chip" aria-label="Illustrative nutrition summary">
              <p className="eyebrow">Sample summary</p>
              <ul>
                <li><span>Energy</span><strong>176 kcal</strong></li>
                <li><span>Protein</span><strong>5.6 g</strong></li>
                <li><span>Carbs</span><strong>34 g</strong></li>
                <li><span>Fat</span><strong>1.5 g</strong></li>
              </ul>
              <p className="muted">Illustration only</p>
            </aside>
          </figure>
        </div>
      </section>

      <section className="progress-story" aria-labelledby="progress-heading">
        <div className="stack">
          <p className="eyebrow">Your goals, your progress</p>
          <h2 id="progress-heading">See logged meals beside the targets you chose.</h2>
          <p className="muted">
            See what you have logged, compare your intake with your goals, and understand how your habits
            change over time. Days without saved meals stay empty on the chart.
          </p>
        </div>
        <div className="progress-visuals">
          <article className="sample-card" aria-label="Illustrative daily summary">
            <p className="eyebrow">Daily summary · sample</p>
            <p className="sample-kcal">1,420 / 1,800 kcal</p>
            <p className="muted">Below target in this illustration</p>
            <div className="mini-bar"><i style={{ width: "79%" }} /></div>
            <p className="muted">Protein 54 g · Carbs 180 g · Fat 48 g</p>
          </article>
          <article className="sample-card" aria-label="Illustrative weekly progress">
            <p className="eyebrow">Weekly view · sample</p>
            <ul className="sample-week" aria-hidden="true">
              {SAMPLE_WEEK.map((height, index) => (
                <li key={index}>
                  <span className="sample-col"><i style={{ height: height ? `${height}%` : "8%" }} className={height ? undefined : "is-empty"} /></span>
                  <span>{["M", "T", "W", "T", "F", "S", "S"][index]}</span>
                </li>
              ))}
            </ul>
            <p className="muted">Filled days have saved meals. Empty days are no data.</p>
          </article>
        </div>
      </section>

      <section className="converse-split" aria-labelledby="chat-heading">
        <div className="stack">
          <p className="eyebrow">A conversation that helps you log</p>
          <h2 id="chat-heading">Describe the meal. Confirm it. Then it counts.</h2>
          <p className="muted">
            The nutrition assistant helps you identify foods and quantities. If two foods share a name, or
            an amount is missing, it asks before anything is saved. Suggestions and drafts are not eaten
            meals.
          </p>
        </div>
        <aside className="chat-preview" aria-label="Illustrative conversation">
          <p className="eyebrow">Example conversation</p>
          <p className="preview-user">I had a bowl of sambar and two idlis.</p>
          <p className="preview-assist">Which sambar did you mean, and how large was the bowl?</p>
          <p className="preview-user">Medium bowl, and the idlis as two pieces.</p>
          <p className="preview-assist">Check this meal before I log it as breakfast.</p>
        </aside>
      </section>

      <section className="routine" aria-labelledby="routine-heading">
        <p className="eyebrow">Designed around your everyday routine</p>
        <h2 id="routine-heading">The tools that are ready today.</h2>
        <div className="routine-grid">
          {FEATURES.map(([title, copy], index) => (
            <article key={title} className={`routine-item is-${index}`}>
              <h3>{title}</h3>
              <p className="muted">{copy}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="closing closing-editorial">
        <div className="stack">
          <p className="script">Good food, honestly recorded</p>
          <h2>Start with the meal in front of you.</h2>
          <p className="muted">Set your profile, log what you eat, and follow progress from verified nutrition.</p>
          <div className="row-actions">
            <Link className="button" to={user ? "/log" : "/register"}>{user ? "Log a Meal" : "Create an account"}</Link>
            <Link className="soft" to={user ? "/progress" : "/login"}>{user ? "Explore Your Progress" : "Login"}</Link>
          </div>
        </div>
        <figure className="closing-photo">
          <img src="/landing/plate.jpg" alt="A plate of rice, dal, and vegetables" />
        </figure>
      </section>
    </div>
  );
}
