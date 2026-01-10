import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, api } from "@/lib/api";
import type { FetchStrategy, Vertical, WatchTarget, WatchTargetInput } from "@/lib/types";

const VERTICALS: Vertical[] = ["pricing", "compliance", "regulatory", "status", "docs", "generic"];
const STRATEGIES: FetchStrategy[] = ["auto", "api", "browser"];

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  target?: WatchTarget | null;
}

export function TargetFormDialog({ open, onOpenChange, target }: Props) {
  const queryClient = useQueryClient();
  const editing = Boolean(target);

  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [vertical, setVertical] = useState<Vertical>("generic");
  const [strategy, setStrategy] = useState<FetchStrategy>("auto");
  const [interval, setIntervalMinutes] = useState("1440");
  const [instructions, setInstructions] = useState("");
  const [schemaText, setSchemaText] = useState("{}");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setName(target?.name ?? "");
    setUrl(target?.url ?? "");
    setVertical(target?.vertical ?? "generic");
    setStrategy(target?.fetch_strategy ?? "auto");
    setIntervalMinutes(String(target?.check_interval_minutes ?? 1440));
    setInstructions(target?.watch_instructions ?? "");
    setSchemaText(JSON.stringify(target?.extraction_schema ?? {}, null, 2));
    setError(null);
  }, [open, target]);

  const mutation = useMutation({
    mutationFn: (payload: WatchTargetInput) =>
      editing ? api.updateTarget(target!.uuid, payload) : api.createTarget(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["targets"] });
      onOpenChange(false);
    },
    onError: (err) => {
      setError(err instanceof ApiError ? JSON.stringify(err.details) : String(err));
    },
  });

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    let schema: unknown;
    try {
      schema = JSON.parse(schemaText || "{}");
    } catch {
      setError("Extraction schema must be valid JSON.");
      return;
    }
    if (typeof schema !== "object" || schema === null || Array.isArray(schema)) {
      setError('Extraction schema must be a JSON object, e.g. {"price": "number"}.');
      return;
    }
    mutation.mutate({
      name,
      url,
      vertical,
      fetch_strategy: strategy,
      check_interval_minutes: Number(interval),
      watch_instructions: instructions,
      extraction_schema: schema as Record<string, string>,
    });
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{editing ? "Edit target" : "Add watch target"}</DialogTitle>
          <DialogDescription>Define the page to watch and what matters on it.</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="grid gap-4">
          <div className="grid gap-1.5">
            <Label htmlFor="name">Name</Label>
            <Input id="name" value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="url">URL</Label>
            <Input
              id="url"
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.gov/rules"
              required
            />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div className="grid gap-1.5">
              <Label htmlFor="vertical">Vertical</Label>
              <Select
                id="vertical"
                value={vertical}
                onChange={(e) => setVertical(e.target.value as Vertical)}
              >
                {VERTICALS.map((v) => (
                  <option key={v} value={v}>
                    {v}
                  </option>
                ))}
              </Select>
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="strategy">Fetch</Label>
              <Select
                id="strategy"
                value={strategy}
                onChange={(e) => setStrategy(e.target.value as FetchStrategy)}
              >
                {STRATEGIES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </Select>
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="interval">Interval (min)</Label>
              <Input
                id="interval"
                type="number"
                min={5}
                value={interval}
                onChange={(e) => setIntervalMinutes(e.target.value)}
              />
            </div>
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="instructions">What to watch</Label>
            <Textarea
              id="instructions"
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              placeholder="e.g. the headline price, or new data-retention clauses"
            />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="schema">Extraction schema (JSON)</Label>
            <Textarea
              id="schema"
              className="font-mono text-xs"
              value={schemaText}
              onChange={(e) => setSchemaText(e.target.value)}
              placeholder='{"price": "number", "in_stock": "boolean"}'
            />
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Saving…" : editing ? "Save changes" : "Add target"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
