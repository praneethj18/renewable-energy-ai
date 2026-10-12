import type { ReactNode } from "react";
import { XCircle } from "lucide-react";

export function MetricCard({
  label,
  value,
  detail,
  icon,
}: {
  label: string;
  value: string;
  detail: string;
  icon: ReactNode;
}) {
  return (
    <article className="metric-card">
      <div className="metric-top">
        <span>{label}</span>
        <span className="metric-icon">{icon}</span>
      </div>
      <strong className="metric-value">{value}</strong>
      <span className="metric-detail">{detail}</span>
    </article>
  );
}

export function ErrorBanner({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="error-banner" role="alert">
      <XCircle size={19} />
      <span>{message}</span>
      <button onClick={onRetry}>Retry</button>
    </div>
  );
}
