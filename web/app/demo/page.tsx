"use client";

import { Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { api } from "@/lib/api-client";

const DEMO_TEXT =
  "2b2b under $3,800 near Sunnyvale Caltrain, 20 min to Santa Clara, dog friendly";

export default function DemoPage() {
  const router = useRouter();
  const started = useRef(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    (async () => {
      try {
        const brief = await api.createBrief({ text: DEMO_TEXT });
        const { run_id } = await api.createRun(brief.id);
        router.replace(`/runs/${run_id}`);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not start the demo run.");
      }
    })();
  }, [router]);

  return (
    <div className="container flex min-h-[60vh] flex-col items-center justify-center gap-4 text-center">
      {error ? (
        <>
          <h1 className="text-2xl">Demo unavailable</h1>
          <p className="max-w-md text-sm text-muted-foreground">
            {error}. Is the API running? Try <code className="font-mono">make demo</code> first.
          </p>
        </>
      ) : (
        <>
          <Loader2 className="h-8 w-8 animate-spin text-primary" aria-hidden />
          <h1 className="text-2xl">Launching the Sunnyvale demo…</h1>
          <p className="max-w-md text-sm text-muted-foreground">
            Parsing “{DEMO_TEXT}” and dispatching the agent team.
          </p>
        </>
      )}
    </div>
  );
}
