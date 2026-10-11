"use client";

import { ArrowLeft, ArrowRight, Plus, Sparkles, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api, type Place, type SearchBriefInput } from "@/lib/api-client";
import { cn, formatUSD } from "@/lib/utils";

const STEPS = ["Basics", "Places that matter", "Must-haves", "Review"] as const;
const CITIES = ["Sunnyvale", "Santa Clara", "Mountain View", "Cupertino", "San Jose"];
const AMENITIES = [
  "in-unit laundry",
  "parking",
  "dog friendly",
  "cat friendly",
  "air conditioning",
  "dishwasher",
  "gym",
  "pool",
  "balcony",
  "ev charging",
];
const MODES = ["drive", "transit", "bike", "walk"] as const;

const emptyPlace = (): Place => ({
  label: "Work",
  address: "",
  weight: 1.0,
  modes: ["drive", "transit"],
  arrival_time: "09:00",
  tolerance_minutes: 30,
});

const defaultBrief = (): SearchBriefInput => ({
  budget_max: 3500,
  lease_months: 12,
  beds: 2,
  baths: 1,
  pets: [],
  cities: ["Sunnyvale"],
  must_haves: [],
  nice_to_haves: [],
  deal_breakers: [],
  important_places: [emptyPlace()],
  parking_required: false,
  in_unit_laundry_required: false,
  max_listings: 20,
});

function Chip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "rounded-full border px-3 py-1.5 text-sm transition-colors",
        active
          ? "border-primary bg-primary/10 text-primary"
          : "border-border text-muted-foreground hover:border-primary/40",
      )}
    >
      {children}
    </button>
  );
}

export default function BriefBuilderPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [nlMode, setNlMode] = useState(false);
  const [nlText, setNlText] = useState("");
  const [parsing, setParsing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [brief, setBrief] = useState<SearchBriefInput>(defaultBrief);

  // Live NL parse (debounced) — "type a sentence, see it parsed into fields".
  useEffect(() => {
    if (!nlMode || nlText.trim().length < 12) return;
    const timer = setTimeout(async () => {
      setParsing(true);
      try {
        const parsed = await api.createBriefPreview(nlText);
        setBrief((prev) => ({ ...parsed, max_listings: prev.max_listings }));
      } catch {
        /* preview is best-effort */
      } finally {
        setParsing(false);
      }
    }, 700);
    return () => clearTimeout(timer);
  }, [nlMode, nlText]);

  const update = (patch: Partial<SearchBriefInput>) =>
    setBrief((prev) => ({ ...prev, ...patch }));

  const updatePlace = (index: number, patch: Partial<Place>) =>
    setBrief((prev) => ({
      ...prev,
      important_places: (prev.important_places ?? []).map((place, i) =>
        i === index ? { ...place, ...patch } : place,
      ),
    }));

  const canContinue = useMemo(() => {
    if (step === 1) return (brief.important_places ?? []).every((p) => p.address.trim() !== "");
    return true;
  }, [step, brief]);

  const start = async () => {
    setSubmitting(true);
    try {
      const created = await api.createBrief({ brief, text: nlMode ? nlText : undefined });
      const { run_id } = await api.createRun(created.id);
      router.push(`/runs/${run_id}`);
    } catch (e) {
      setSubmitting(false);
      alert(e instanceof Error ? e.message : "failed to start run");
    }
  };

  return (
    <div className="container max-w-3xl py-10">
      <div className="mb-8 flex items-center justify-between">
        <h1 className="text-3xl">New search</h1>
        <Button variant={nlMode ? "default" : "outline"} size="sm" onClick={() => setNlMode(!nlMode)}>
          <Sparkles className="h-4 w-4" /> {nlMode ? "Natural language: on" : "Describe it instead"}
        </Button>
      </div>

      {nlMode && (
        <Card className="mb-6">
          <CardContent className="pt-6">
            <label className="text-sm font-medium" htmlFor="nl-input">
              Describe your ideal place
            </label>
            <textarea
              id="nl-input"
              value={nlText}
              onChange={(e) => setNlText(e.target.value)}
              placeholder="2b2b under $3,800 near Sunnyvale Caltrain, 20 min to Santa Clara, dog friendly"
              className="mt-2 w-full rounded-md border bg-background p-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              rows={3}
            />
            <p className="mt-1 text-xs text-muted-foreground" aria-live="polite">
              {parsing ? "Parsing…" : "Fields below update as you type."}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Progress */}
      <nav aria-label="Progress" className="mb-8">
        <ol className="flex items-center gap-2">
          {STEPS.map((label, i) => (
            <li key={label} className="flex flex-1 items-center gap-2">
              <button
                type="button"
                onClick={() => i < step && setStep(i)}
                className={cn(
                  "flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-xs font-medium",
                  i < step && "border-primary bg-primary text-primary-foreground",
                  i === step && "border-primary text-primary",
                  i > step && "border-border text-muted-foreground",
                )}
                aria-current={i === step ? "step" : undefined}
              >
                {i + 1}
              </button>
              <span
                className={cn(
                  "hidden text-xs sm:block",
                  i === step ? "text-foreground" : "text-muted-foreground",
                )}
              >
                {label}
              </span>
              {i < STEPS.length - 1 && <div className="h-px flex-1 bg-border" />}
            </li>
          ))}
        </ol>
      </nav>

      {step === 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Basics</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div>
              <label className="flex items-baseline justify-between text-sm font-medium">
                Max monthly budget
                <span className="font-serif text-xl text-primary">
                  {formatUSD(brief.budget_max)}
                </span>
              </label>
              <input
                type="range"
                min={1200}
                max={8000}
                step={50}
                value={brief.budget_max}
                onChange={(e) => update({ budget_max: Number(e.target.value) })}
                className="mt-2 w-full accent-[hsl(var(--primary))]"
                aria-label="Max monthly budget"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <label className="text-sm font-medium">
                Bedrooms
                <select
                  value={brief.beds ?? 1}
                  onChange={(e) => update({ beds: Number(e.target.value) })}
                  className="mt-1 w-full rounded-md border bg-background p-2 text-sm"
                >
                  <option value={0}>Studio</option>
                  {[1, 2, 3].map((n) => (
                    <option key={n} value={n}>
                      {n}+
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-sm font-medium">
                Bathrooms
                <select
                  value={brief.baths ?? 1}
                  onChange={(e) => update({ baths: Number(e.target.value) })}
                  className="mt-1 w-full rounded-md border bg-background p-2 text-sm"
                >
                  {[1, 1.5, 2, 3].map((n) => (
                    <option key={n} value={n}>
                      {n}+
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div>
              <p className="text-sm font-medium">Cities</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {CITIES.map((city) => {
                  const active = (brief.cities ?? []).includes(city);
                  return (
                    <Chip
                      key={city}
                      active={active}
                      onClick={() =>
                        update({
                          cities: active
                            ? (brief.cities ?? []).filter((c) => c !== city)
                            : [...(brief.cities ?? []), city],
                        })
                      }
                    >
                      {city}
                    </Chip>
                  );
                })}
              </div>
            </div>
            <label className="block text-sm font-medium">
              Earliest move-in
              <input
                type="date"
                value={brief.move_in_earliest ?? ""}
                onChange={(e) => update({ move_in_earliest: e.target.value || null })}
                className="mt-1 w-full rounded-md border bg-background p-2 text-sm"
              />
            </label>
          </CardContent>
        </Card>
      )}

      {step === 1 && (
        <Card>
          <CardHeader>
            <CardTitle>Places that matter</CardTitle>
            <p className="text-sm text-muted-foreground">
              Work, gym, friends — we score every listing's commute to each.
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            {(brief.important_places ?? []).map((place, i) => (
              <div key={i} className="rounded-lg border p-4">
                <div className="flex gap-2">
                  <input
                    value={place.label}
                    onChange={(e) => updatePlace(i, { label: e.target.value })}
                    placeholder="Label (e.g. Work)"
                    aria-label="Place label"
                    className="w-32 rounded-md border bg-background p-2 text-sm"
                  />
                  <input
                    value={place.address}
                    onChange={(e) => updatePlace(i, { address: e.target.value })}
                    placeholder="Address or landmark (e.g. Santa Clara)"
                    aria-label="Place address"
                    className="flex-1 rounded-md border bg-background p-2 text-sm"
                  />
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label="Remove place"
                    onClick={() =>
                      update({
                        important_places: (brief.important_places ?? []).filter((_, j) => j !== i),
                      })
                    }
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
                <div className="mt-3 grid gap-3 sm:grid-cols-3">
                  <label className="text-xs text-muted-foreground">
                    Importance: {Math.round((place.weight ?? 1) * 100)}%
                    <input
                      type="range"
                      min={0.1}
                      max={1}
                      step={0.1}
                      value={place.weight ?? 1}
                      onChange={(e) => updatePlace(i, { weight: Number(e.target.value) })}
                      className="w-full accent-[hsl(var(--primary))]"
                    />
                  </label>
                  <label className="text-xs text-muted-foreground">
                    Arrive by
                    <input
                      type="time"
                      value={place.arrival_time ?? "09:00"}
                      onChange={(e) => updatePlace(i, { arrival_time: e.target.value })}
                      className="mt-1 w-full rounded-md border bg-background p-1.5 text-sm text-foreground"
                    />
                  </label>
                  <label className="text-xs text-muted-foreground">
                    OK up to (min)
                    <input
                      type="number"
                      min={5}
                      max={120}
                      value={place.tolerance_minutes ?? 30}
                      onChange={(e) => updatePlace(i, { tolerance_minutes: Number(e.target.value) })}
                      className="mt-1 w-full rounded-md border bg-background p-1.5 text-sm text-foreground"
                    />
                  </label>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {MODES.map((mode) => {
                    const active = (place.modes ?? []).includes(mode);
                    return (
                      <Chip
                        key={mode}
                        active={active}
                        onClick={() =>
                          updatePlace(i, {
                            modes: active
                              ? (place.modes ?? []).filter((m) => m !== mode)
                              : [...(place.modes ?? []), mode],
                          })
                        }
                      >
                        {mode}
                      </Chip>
                    );
                  })}
                </div>
              </div>
            ))}
            <Button
              variant="outline"
              onClick={() =>
                update({ important_places: [...(brief.important_places ?? []), emptyPlace()] })
              }
            >
              <Plus className="h-4 w-4" /> Add place
            </Button>
          </CardContent>
        </Card>
      )}

      {step === 2 && (
        <Card>
          <CardHeader>
            <CardTitle>Must-haves & deal-breakers</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {(
              [
                ["Must-haves", "must_haves"],
                ["Nice-to-haves", "nice_to_haves"],
              ] as const
            ).map(([label, key]) => (
              <div key={key}>
                <p className="text-sm font-medium">{label}</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {AMENITIES.map((amenity) => {
                    const list = brief[key] ?? [];
                    const active = list.includes(amenity);
                    return (
                      <Chip
                        key={amenity}
                        active={active}
                        onClick={() =>
                          update({
                            [key]: active
                              ? list.filter((a) => a !== amenity)
                              : [...list, amenity],
                          } as Partial<SearchBriefInput>)
                        }
                      >
                        {amenity}
                      </Chip>
                    );
                  })}
                </div>
              </div>
            ))}
            <div>
              <p className="text-sm font-medium">Pets</p>
              <div className="mt-2 flex gap-2">
                {["dog", "cat"].map((pet) => {
                  const active = (brief.pets ?? []).includes(pet);
                  return (
                    <Chip
                      key={pet}
                      active={active}
                      onClick={() =>
                        update({
                          pets: active
                            ? (brief.pets ?? []).filter((p) => p !== pet)
                            : [...(brief.pets ?? []), pet],
                        })
                      }
                    >
                      {pet} 🐾
                    </Chip>
                  );
                })}
              </div>
            </div>
            <label className="block text-sm font-medium">
              Deal-breakers (comma separated)
              <input
                value={(brief.deal_breakers ?? []).join(", ")}
                onChange={(e) =>
                  update({
                    deal_breakers: e.target.value
                      .split(",")
                      .map((s) => s.trim())
                      .filter(Boolean),
                  })
                }
                placeholder="e.g. ground floor, no dishwasher"
                className="mt-1 w-full rounded-md border bg-background p-2 text-sm"
              />
            </label>
          </CardContent>
        </Card>
      )}

      {step === 3 && (
        <Card>
          <CardHeader>
            <CardTitle>Review your brief</CardTitle>
            <p className="text-sm text-muted-foreground">
              This is what the agent team will work from. Go back to edit anything.
            </p>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <p>
              <strong className="font-serif text-lg">
                {brief.beds === 0 ? "Studio" : `${brief.beds}+ bed`}, {brief.baths}+ bath
              </strong>{" "}
              up to <strong>{formatUSD(brief.budget_max)}/mo</strong> in{" "}
              {(brief.cities ?? []).join(", ") || "any city"}
            </p>
            <div className="flex flex-wrap gap-1.5">
              {(brief.important_places ?? []).map((place, i) => (
                <Badge key={i} variant="secondary">
                  {place.label}: {place.address} (≤{place.tolerance_minutes} min)
                </Badge>
              ))}
            </div>
            <div className="flex flex-wrap gap-1.5">
              {(brief.must_haves ?? []).map((m) => (
                <Badge key={m} variant="verified">
                  must: {m}
                </Badge>
              ))}
              {(brief.nice_to_haves ?? []).map((m) => (
                <Badge key={m} variant="secondary">
                  nice: {m}
                </Badge>
              ))}
              {(brief.deal_breakers ?? []).map((m) => (
                <Badge key={m} variant="high">
                  avoid: {m}
                </Badge>
              ))}
              {(brief.pets ?? []).map((p) => (
                <Badge key={p} variant="outline">
                  {p}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="mt-6 flex justify-between">
        <Button variant="ghost" disabled={step === 0} onClick={() => setStep(step - 1)}>
          <ArrowLeft className="h-4 w-4" /> Back
        </Button>
        {step < STEPS.length - 1 ? (
          <Button disabled={!canContinue} onClick={() => setStep(step + 1)}>
            Continue <ArrowRight className="h-4 w-4" />
          </Button>
        ) : (
          <Button size="lg" disabled={submitting} onClick={start}>
            {submitting ? "Dispatching agents…" : "Start the search"}
            <ArrowRight className="h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  );
}
