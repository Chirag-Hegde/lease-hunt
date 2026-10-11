import {
  Banknote,
  Bike,
  FileSearch,
  MessageSquareQuote,
  Search,
  ShieldCheck,
} from "lucide-react";

import { LandingSearchBox } from "@/components/landing/search-box";
import { Badge } from "@/components/ui/badge";

const agents = [
  { name: "Scout", icon: Search, role: "Finds and dedupes listings that match your brief." },
  { name: "Commute", icon: Bike, role: "Scores drive, transit, bike & walk times to your places." },
  {
    name: "Review",
    icon: MessageSquareQuote,
    role: "Mines reviews and Reddit for recurring building complaints.",
  },
  { name: "Price", icon: Banknote, role: "Benchmarks rent against true comps and total cost." },
  { name: "Lease", icon: FileSearch, role: "Flags risky clauses in your lease with exact citations." },
  { name: "Critic", icon: ShieldCheck, role: "Verifies every claim has evidence before you see it." },
];

export default function LandingPage() {
  return (
    <div className="container flex flex-col gap-20 py-16">
      {/* Hero — server-rendered; animations are CSS-only (compositor friendly) */}
      <section className="mx-auto flex max-w-3xl flex-col items-center gap-6 text-center">
        <Badge variant="secondary">Multi-agent apartment hunting</Badge>
        <h1 className="text-5xl leading-tight md:text-6xl">
          Your apartment hunt, handled by a{" "}
          <span className="text-primary">team of AI agents</span>.
        </h1>
        <p className="max-w-xl text-lg text-muted-foreground">
          Ranked listings, commute scores, building red flags, clause-level lease analysis, and an
          evidence-backed negotiation draft — in minutes, every claim checked by a Critic agent.
        </p>

        {/* Agent relay */}
        <div className="flex items-center gap-1.5 py-2" aria-hidden>
          {agents.map((agent, i) => (
            <div key={agent.name} className="flex items-center gap-1.5">
              <div
                className="flex h-10 w-10 animate-bob items-center justify-center rounded-full border bg-card text-primary shadow-soft"
                style={{ animationDelay: `${i * 0.35}s` }}
                title={agent.name}
              >
                <agent.icon className="h-4 w-4" />
              </div>
              {i < agents.length - 1 && (
                <div
                  className="h-px w-5 animate-pulse-line bg-border"
                  style={{ animationDelay: `${i * 0.35 + 0.15}s` }}
                />
              )}
            </div>
          ))}
        </div>

        <LandingSearchBox />
      </section>

      {/* Agents */}
      <section aria-label="The agent team">
        <h2 className="text-center text-3xl">Six specialists, one shortlist</h2>
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {agents.map((agent, i) => (
            <div
              key={agent.name}
              className="animate-fade-up rounded-lg border bg-card p-5 shadow-soft"
              style={{ animationDelay: `${i * 0.05}s` }}
            >
              <agent.icon className="h-5 w-5 text-primary" aria-hidden />
              <h3 className="mt-3 font-serif text-lg">{agent.name} Agent</h3>
              <p className="mt-1 text-sm text-muted-foreground">{agent.role}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Lease red-flag sample */}
      <section className="mx-auto w-full max-w-3xl" aria-label="Sample lease finding">
        <h2 className="text-center text-3xl">It reads the lease so you don't sign blind</h2>
        <div className="mt-8 rounded-lg border bg-card p-6 shadow-soft">
          <div className="rounded-md border bg-muted/40 p-4 font-mono text-xs leading-relaxed">
            <p className="text-muted-foreground">18. WAIVER OF LIABILITY AND INDEMNIFICATION</p>
            <p className="mt-1">
              Tenant releases Landlord from any and all liability for injury, loss, or damage{" "}
              <mark className="rounded bg-severity-high/20 px-1 text-foreground">
                arising from any cause whatsoever, including Landlord's own negligence
              </mark>
              , and agrees to indemnify and hold Landlord harmless from all claims.
            </p>
          </div>
          <div className="mt-4 flex items-start gap-3">
            <Badge variant="high">High risk</Badge>
            <div className="text-sm">
              <p>
                You'd be waiving the right to hold the landlord responsible even for their own
                negligence.
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Cal. Civ. Code §1953(a): this waiver is void as contrary to public policy →{" "}
                <span className="text-primary">ask to strike it</span>. Every finding cites the
                exact page and clause, with an official source link.
              </p>
            </div>
          </div>
        </div>
        <p className="mt-3 text-center text-xs text-muted-foreground">
          Not legal advice. Verify with a local tenant rights organization or attorney.
        </p>
      </section>
    </div>
  );
}
