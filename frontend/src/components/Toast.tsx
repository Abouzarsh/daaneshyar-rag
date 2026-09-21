import { AlertCircle, CheckCircle2, X } from "lucide-react";

export interface ToastData {
  id: number;
  message: string;
  tone: "success" | "error";
}

interface ToastProps {
  items: ToastData[];
  onDismiss: (id: number) => void;
}

export function Toasts({ items, onDismiss }: ToastProps) {
  return (
    <div className="toast-stack" aria-live="polite">
      {items.map((item) => (
        <div className={"toast " + item.tone} key={item.id}>
          {item.tone === "success" ? (
            <CheckCircle2 size={19} />
          ) : (
            <AlertCircle size={19} />
          )}
          <span>{item.message}</span>
          <button onClick={() => onDismiss(item.id)} aria-label="بستن">
            <X size={16} />
          </button>
        </div>
      ))}
    </div>
  );
}
