import type { ReactNode } from "react";

export default function AuthPageLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-svh bg-white flex items-center justify-center font-[system-ui,'Segoe_UI',Roboto,sans-serif] text-[#6b6375] text-lg leading-[145%] tracking-[0.18px] antialiased max-lg:text-base">
      <style>{`
        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          20% { transform: translateX(-6px); }
          40% { transform: translateX(6px); }
          60% { transform: translateX(-4px); }
          80% { transform: translateX(4px); }
        }
        .animate-shake { animation: shake 0.4s ease-in-out; }
      `}</style>
      {children}
    </div>
  );
}
