import { useParams } from "react-router-dom";

export function TargetDetail() {
  const { uuid } = useParams<{ uuid: string }>();
  return (
    <div className="mx-auto max-w-5xl space-y-1">
      <h1 className="text-2xl font-semibold tracking-tight">Target detail</h1>
      <p className="text-muted-foreground">
        Change timeline and before/after diff viewer for{" "}
        <code className="rounded bg-muted px-1 py-0.5 text-xs">{uuid}</code> land here.
      </p>
    </div>
  );
}
