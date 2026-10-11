"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { API_URL } from "@/lib/api-client";
import { formatUSD } from "@/lib/utils";

type Settings = {
  demo_mode: boolean;
  llm_provider: string;
  run_budget_usd: number;
  run_budget_tokens: number;
  fanout_concurrency: number;
  lease_retention_days: number;
  keys: Record<string, boolean>;
};

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const { data } = useQuery({
    queryKey: ["settings"],
    queryFn: async () => {
      const resp = await fetch(`${API_URL}/api/settings`);
      if (!resp.ok) throw new Error(await resp.text());
      return (await resp.json()) as Settings;
    },
  });

  const mutation = useMutation({
    mutationFn: async (patch: Partial<Settings>) => {
      const resp = await fetch(`${API_URL}/api/settings`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      });
      if (!resp.ok) throw new Error(await resp.text());
      return (await resp.json()) as Settings;
    },
    onSuccess: (next) => queryClient.setQueryData(["settings"], next),
  });

  if (!data) {
    return <div className="container max-w-2xl py-10"><div className="skeleton h-80" /></div>;
  }

  return (
    <div className="container max-w-2xl space-y-6 py-10">
      <h1 className="text-3xl">Settings</h1>

      <Card>
        <CardHeader>
          <CardTitle>Mode & model</CardTitle>
          <CardDescription>
            Demo mode runs fully offline with mock providers. Set keys in{" "}
            <code className="font-mono text-xs">backend/.env</code> to enable real providers.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between text-sm">
            <span>Demo mode</span>
            <Badge variant={data.demo_mode ? "verified" : "secondary"}>
              {data.demo_mode ? "on (offline)" : "off"}
            </Badge>
          </div>
          <label className="flex items-center justify-between text-sm">
            <span>LLM provider</span>
            <select
              value={data.llm_provider}
              onChange={(e) => mutation.mutate({ llm_provider: e.target.value })}
              className="rounded-md border bg-background p-1.5 text-sm"
            >
              <option value="mock">mock (offline)</option>
              <option value="anthropic" disabled={!data.keys.anthropic}>
                anthropic {data.keys.anthropic ? "" : "(no key)"}
              </option>
              <option value="openai" disabled={!data.keys.openai}>
                openai {data.keys.openai ? "" : "(no key)"}
              </option>
            </select>
          </label>
          {mutation.isError && (
            <p className="text-xs text-severity-high">{String(mutation.error)}</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Run budget</CardTitle>
          <CardDescription>
            Runs abort gracefully with partial results when the budget is hit.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <label className="block text-sm">
            <span className="flex justify-between">
              Dollar cap per run <strong>{formatUSD(data.run_budget_usd, 2)}</strong>
            </span>
            <input
              type="range"
              min={0.05}
              max={5}
              step={0.05}
              value={data.run_budget_usd}
              onChange={(e) => mutation.mutate({ run_budget_usd: Number(e.target.value) })}
              className="mt-1 w-full accent-[hsl(var(--primary))]"
            />
          </label>
          <label className="flex items-center justify-between text-sm">
            <span>Parallel listings analyzed at once</span>
            <input
              type="number"
              min={1}
              max={20}
              value={data.fanout_concurrency}
              onChange={(e) => mutation.mutate({ fanout_concurrency: Number(e.target.value) })}
              className="w-20 rounded-md border bg-background p-1.5 text-sm"
            />
          </label>
          <p className="text-xs text-muted-foreground">
            Lease PDFs auto-delete after {data.lease_retention_days} days.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>API keys</CardTitle>
          <CardDescription>Presence only — key values are never displayed or sent.</CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="grid grid-cols-2 gap-2 text-sm">
            {Object.entries(data.keys).map(([name, present]) => (
              <li key={name} className="flex items-center gap-2">
                {present ? (
                  <Check className="h-4 w-4 text-primary" />
                ) : (
                  <X className="h-4 w-4 text-muted-foreground/50" />
                )}
                <span className={present ? "" : "text-muted-foreground"}>{name}</span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
