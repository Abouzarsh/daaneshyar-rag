import {
  Menu,
  Moon,
  PanelRightOpen,
  Sun,
} from "lucide-react";
import type { HealthStatus, ViewName } from "../types";

interface TopbarProps {
  view: ViewName;
  health: HealthStatus | null;
  dark: boolean;
  onToggleTheme: () => void;
  onOpenMenu: () => void;
}

const titles: Record<ViewName, string> = {
  chat: "گفت‌وگو با اسناد",
  documents: "کتابخانه اسناد",
  about: "درباره دانشیار",
};

export function Topbar({
  view,
  health,
  dark,
  onToggleTheme,
  onOpenMenu,
}: TopbarProps) {
  return (
    <header className="topbar">
      <div className="topbar-title">
        <button
          className="icon-button menu-button"
          onClick={onOpenMenu}
          aria-label="باز کردن منو"
        >
          <Menu size={21} />
        </button>
        <PanelRightOpen size={18} />
        <span>{titles[view]}</span>
      </div>
      <div className="topbar-actions">
        <span className="privacy-pill">
          <span
            className={
              "status-dot " +
              (health?.status === "ok" ? "online" : "warning")
            }
          />
          {health?.status === "ok" ? "سامانه آماده است" : "وضعیت محدود"}
        </span>
        <button
          className="icon-button"
          onClick={onToggleTheme}
          aria-label="تغییر پوسته"
        >
          {dark ? <Sun size={18} /> : <Moon size={18} />}
        </button>
      </div>
    </header>
  );
}
