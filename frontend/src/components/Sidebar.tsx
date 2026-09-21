import {
  BookOpenText,
  FileStack,
  Info,
  MessageSquareText,
  MoreHorizontal,
  Plus,
  Trash2,
  X,
} from "lucide-react";
import type {
  ConversationSummary,
  HealthStatus,
  ViewName,
} from "../types";
import { LogoMark } from "./LogoMark";

interface SidebarProps {
  view: ViewName;
  conversations: ConversationSummary[];
  activeConversationId: string | null;
  health: HealthStatus | null;
  mobileOpen: boolean;
  onClose: () => void;
  onViewChange: (view: ViewName) => void;
  onSelectConversation: (id: string) => void;
  onDeleteConversation: (id: string) => void;
  onNewChat: () => void;
}

const navItems: {
  id: ViewName;
  label: string;
  icon: typeof MessageSquareText;
}[] = [
  { id: "chat", label: "گفت‌وگو با اسناد", icon: MessageSquareText },
  { id: "documents", label: "کتابخانه اسناد", icon: FileStack },
  { id: "about", label: "درباره سامانه", icon: Info },
];

function shortDate(value: string) {
  try {
    return new Intl.DateTimeFormat("fa-IR", {
      month: "short",
      day: "numeric",
    }).format(new Date(value));
  } catch {
    return "";
  }
}

export function Sidebar({
  view,
  conversations,
  activeConversationId,
  health,
  mobileOpen,
  onClose,
  onViewChange,
  onSelectConversation,
  onDeleteConversation,
  onNewChat,
}: SidebarProps) {
  const chooseView = (nextView: ViewName) => {
    onViewChange(nextView);
    onClose();
  };

  return (
    <>
      <div
        className={"sidebar-backdrop " + (mobileOpen ? "is-visible" : "")}
        onClick={onClose}
      />
      <aside className={"sidebar " + (mobileOpen ? "is-open" : "")}>
        <div className="brand-row">
          <div className="brand-lockup">
            <LogoMark />
            <div>
              <div className="brand-name">دانشیار</div>
              <div className="brand-tagline">هوش سازمانی، با منبع</div>
            </div>
          </div>
          <button
            className="icon-button sidebar-close"
            onClick={onClose}
            aria-label="بستن منو"
          >
            <X size={20} />
          </button>
        </div>

        <button className="new-chat-button" onClick={onNewChat}>
          <Plus size={19} />
          <span>گفت‌وگوی تازه</span>
          <kbd>+</kbd>
        </button>

        <nav className="main-nav" aria-label="منوی اصلی">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                className={"nav-item " + (view === item.id ? "active" : "")}
                onClick={() => chooseView(item.id)}
              >
                <Icon size={19} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        <div className="sidebar-section-heading">
          <span>گفت‌وگوهای اخیر</span>
          <MoreHorizontal size={18} />
        </div>

        <div className="conversation-list">
          {conversations.length === 0 ? (
            <div className="sidebar-empty">
              <BookOpenText size={22} />
              <p>هنوز گفت‌وگویی ثبت نشده</p>
            </div>
          ) : (
            conversations.slice(0, 12).map((conversation) => (
              <button
                key={conversation.id}
                className={
                  "conversation-item " +
                  (activeConversationId === conversation.id ? "active" : "")
                }
                onClick={() => {
                  onSelectConversation(conversation.id);
                  onClose();
                }}
              >
                <MessageSquareText size={16} />
                <span className="conversation-copy">
                  <strong>{conversation.title}</strong>
                  <small>
                    {shortDate(conversation.updated_at)}
                    <i>·</i>
                    {conversation.message_count} پیام
                  </small>
                </span>
                <span
                  className="conversation-delete"
                  role="button"
                  tabIndex={0}
                  aria-label="حذف گفت‌وگو"
                  onClick={(event) => {
                    event.stopPropagation();
                    onDeleteConversation(conversation.id);
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      event.stopPropagation();
                      onDeleteConversation(conversation.id);
                    }
                  }}
                >
                  <Trash2 size={15} />
                </span>
              </button>
            ))
          )}
        </div>

        <div className="sidebar-footer">
          <span
            className={
              "status-dot " +
              (health?.components.llm?.ok ? "online" : "warning")
            }
          />
          <div>
            <strong>
              {health?.components.llm?.ok
                ? "مدل آماده پاسخ‌گویی"
                : "مدل نیاز به بررسی دارد"}
            </strong>
            <small>
              {health?.components.llm?.model || "در حال بررسی سرویس"}
            </small>
          </div>
        </div>
      </aside>
    </>
  );
}
