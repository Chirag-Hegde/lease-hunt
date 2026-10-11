"use client";

import { motion } from "framer-motion";
import {
  ArrowRight,
  Banknote,
  Bike,
  FileSearch,
  MessageSquareQuote,
  ScanSearch,
  Search,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { api } from "@/lib/api-client";

const agents = [
  { name: "Scout", icon: Search, role: "Finds and dedupes listings that match your brief." },
  { name: "Commute", icon: Bike, role: "Scores drive, transit, bike & walk times to your places." },
  { name: "Review", icon: MessageSquareQuote, role: "Mines reviews and Reddit for recurring building complaints." },
  { name: "Price", icon: Banknote, role: "Benchmarks rent against true comps and total cost." },
  { name: "Lease", icon: FileSearch, role: "Flags risky clauses in your lease with exact citations." },
  { name: "Critic", icon: ShieldCheck, role: "Verifies every claim has evidence before you see it." },
];

const PLACEHOLDER =
  "2b2b under $3,800 near Sunnyvale Caltrain, 20 min to Santa Clara, dog friendly";

export default function LandingPage() {
  const router = useRouter();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);

  const start = async () => {
    setBusy(true);
    try {
      const brief = await api.createBrief({ text: text.trim() || PLACEHOLDER });
      const { run_id } = await api.createRun(brief.id);
      router.push(`/runs/${run_id}`);
    } catch {
      setBusy(false);
      router.push("/new");
    }
  };

  return (
    <div className="container flex flex-col gap-20 py-16">
      {/* Hero */}
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

        {/* Animated agent relay */}
        <div className="flex items-center gap-1.5 py-2" aria-hidden>
          {agents.map((agent, i) => (
            <div key={agent.name} className="flex items-center gap-1.5">
              <motion.div
                className="flex h-10 w-10 items-center justify-center rounded-full border bg-card text-primary shadow-soft"
                animate={{ y: [0, -6, 0] }}
                transition={{ repeat: Infinity, duration: 2.4, delay: i * 0.35 }}
                title={agent.name}
              >
                <agent.icon className="h-4 w-4" />
              </motion.div>
              {i < agents.length - 1 && (
                <motion.div
                  className="h-px w-5 bg-border"
                  animate={{ opacity: [0.3, 1, 0.3] }}
                  transition={{ repeat: Infinity, duration: 2.4, delay: i * 0.35 + 0.15 }}
                />
              )}
            </div>
          ))}
        </div>

        <div className="flex w-full max-w-xl flex-col gap-3">
          <div className="flex gap-2 rounded-lg border bg-card p-2 shadow-soft focus-within:ring-2 focus-within:ring-ring">
            <input
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !busy && start()}
              placeholder={PLACEHOLDER}
              aria-label="Describe your ideal apartment"
              className="flex-1 bg-transparent px-2 text-sm focus:outline-none"
            />
            <Button onClick={start} disabled={busy}>
              {busy ? "Dispatching…" : "Search"} <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
          <div className="flex justify-center gap-3 text-sm">
            <Link href="/demo" className={buttonVariants({ variant: "outline", size: "sm" })}>
              <ScanSearch className="h-3.5 w-3.5" /> Try the demo (Sunnyvale)
            </Link>
            <Link href="/new" className={buttonVariants({ variant: "ghost", size: "sm" })}>
              or build a brief step by step
            </Link>
          </div>
        </div>
      </section>

      {/* Agents */}
      <section aria-label="The agent team">
        <h2 className="text-center text-3xl">Six specialists, one shortlist</h2>
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {agents.map((agent, i) => (
            <motion.div
              key={agent.name}
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.05 }}
              className="rounded-lg border bg-card p-5 shadow-soft"
            >
              <agent.icon className="h-5 w-5 text-primary" aria-hidden />
              <h3 className="mt-3 font-serif text-lg">{agent.name} Agent</h3>
              <p className="mt-1 text-sm text-muted-foreground">{agent.role}</p>
            </motion.div>
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
