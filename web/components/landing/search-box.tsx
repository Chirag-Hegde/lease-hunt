"use client";

import { ArrowRight, ScanSearch } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button, buttonVariants } from "@/components/ui/button";
import { api } from "@/lib/api-client";

const PLACEHOLDER =
  "2b2b under $3,800 near Sunnyvale Caltrain, 20 min to Santa Clara, dog friendly";

export function LandingSearchBox() {
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
  );
}
