import type { ReactNode } from "react";
import { ChevronDown } from "lucide-react";

export function EmptyState({ children }: { children: string }) {
  return <div className="py-8 text-center text-sm text-[#6b6375]">{children}</div>;
}

export function ExportSection({
  title,
  children,
  action,
  defaultOpen = false,
  collapsible = true,
}: {
  title: string;
  children: ReactNode;
  action?: ReactNode;
  defaultOpen?: boolean;
  collapsible?: boolean;
}) {
  if (!collapsible) {
    return (
      <section className="bg-white rounded-lg border border-[#e5e4e7] shadow-[0_2px_8px_rgba(0,0,0,0.06)] overflow-hidden">
        <div className="flex items-center justify-between gap-4 border-b border-[#e5e4e7] px-5 py-3">
          <h2 className="text-sm font-bold uppercase tracking-wider text-[#08060d]">{title}</h2>
          {action}
        </div>
        {children}
      </section>
    );
  }

  return (
    <details
      className="group bg-white rounded-lg border border-[#e5e4e7] shadow-[0_2px_8px_rgba(0,0,0,0.06)] overflow-hidden"
      open={defaultOpen}
    >
      <summary className="flex cursor-pointer list-none items-center justify-between gap-4 px-5 py-3 text-sm font-bold uppercase tracking-wider text-[#08060d] marker:hidden">
        <span className="inline-flex items-center gap-2">
          <ChevronDown
            size={16}
            className="-rotate-90 text-[#8c2d19] transition-transform duration-200 group-open:rotate-0"
          />
          {title}
        </span>
        {action}
      </summary>
      <div className="border-t border-[#e5e4e7]">{children}</div>
    </details>
  );
}
