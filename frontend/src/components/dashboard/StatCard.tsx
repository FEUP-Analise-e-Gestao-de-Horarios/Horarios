import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: number;
  icon: LucideIcon;
  color: string;
  processing?: boolean;
}

export default function StatCard({ label, value, icon: Icon, color, processing }: StatCardProps) {
  const pending = processing && value === 0;

  return (
    <div className="flex-1 min-w-[100px] bg-white rounded-lg border border-[#e5e4e7] shadow-[0_2px_8px_rgba(0,0,0,0.06)] p-4 flex flex-col gap-3">
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${color}`}>
        <Icon size={18} />
      </div>
      <div>
        {pending ? (
          <div className="flex gap-1 items-end h-8">
            <span className="w-1.5 h-1.5 rounded-full bg-[#6b6375] animate-bounce [animation-delay:0ms]" />
            <span className="w-1.5 h-1.5 rounded-full bg-[#6b6375] animate-bounce [animation-delay:150ms]" />
            <span className="w-1.5 h-1.5 rounded-full bg-[#6b6375] animate-bounce [animation-delay:300ms]" />
          </div>
        ) : (
          <p className="text-2xl font-bold text-[#08060d] leading-none">{value}</p>
        )}
        <p className="mt-1 text-xs text-[#6b6375]">{label}</p>
      </div>
    </div>
  );
}
