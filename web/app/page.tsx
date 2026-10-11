import { ArrowRight } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const agents = [
  { name: "Scout", role: "Finds and dedupes listings that match your brief." },
  { name: "Commute", role: "Scores drive, transit, bike & walk times to your places." },
  { name: "Review", role: "Mines reviews and Reddit for recurring building complaints." },
  { name: "Price", role: "Benchmarks rent against true comps and total cost." },
  { name: "Lease", role: "Flags risky clauses in your lease with exact citations." },
  { name: "Negotiator", role: "Drafts an evidence-backed negotiation email." },
];

export default function LandingPage() {
  return (
    <div className="container flex flex-col gap-16 py-16">
      <section className="mx-auto flex max-w-3xl flex-col items-center gap-6 text-center">
        <Badge variant="secondary">Multi-agent apartment hunting</Badge>
        <h1 className="text-5xl leading-tight md:text-6xl">
          Your apartment hunt, handled by a <span className="text-primary">team of AI agents</span>.
        </h1>
        <p className="max-w-xl text-lg text-muted-foreground">
          Ranked listings, commute scores, building red flags, lease analysis, and a negotiation
          draft — every claim backed by evidence and checked by a Critic agent.
        </p>
        <div className="flex gap-3">
          <Link href="/new" className={buttonVariants({ size: "lg" })}>
            Start a search <ArrowRight className="h-4 w-4" />
          </Link>
          <Link href="/demo" className={buttonVariants({ size: "lg", variant: "outline" })}>
            Try the demo (Sunnyvale)
          </Link>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {agents.map((agent) => (
          <Card key={agent.name} className="animate-fade-up">
            <CardHeader>
              <CardTitle>{agent.name} Agent</CardTitle>
              <CardDescription>{agent.role}</CardDescription>
            </CardHeader>
            <CardContent />
          </Card>
        ))}
      </section>
    </div>
  );
}
