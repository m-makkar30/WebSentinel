import { useMutation, useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { api } from "@/lib/api";
import type { WatchTarget } from "@/lib/types";

interface Props {
  target: WatchTarget;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function DeleteTargetDialog({ target, open, onOpenChange }: Props) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => api.deleteTarget(target.uuid),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["targets"] });
      onOpenChange(false);
    },
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Delete target</DialogTitle>
          <DialogDescription>
            This permanently removes “{target.name}” and all its snapshots, changes, and alerts.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
          >
            {mutation.isPending ? "Deleting…" : "Delete"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
