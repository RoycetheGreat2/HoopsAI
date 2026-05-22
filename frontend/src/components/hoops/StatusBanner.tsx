
import { CheckCircle } from 'lucide-react';

export function StatusBanner() {
  return (
    <div className="mb-6 rounded-lg border border-secondary/30 bg-secondary/5 p-4 flex items-center gap-3">
      <CheckCircle className="w-5 h-5 text-secondary flex-shrink-0" />
      <div>
        <p className="text-sm font-medium text-foreground">System Status: Operational</p>
        <p className="text-xs text-muted-foreground">All models running • Last updated 2 minutes ago</p>
      </div>
    </div>
  );
}
