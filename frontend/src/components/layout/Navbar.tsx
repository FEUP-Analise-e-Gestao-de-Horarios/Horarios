import { useLogout } from "@/api/hooks/useAuth";
import { ROUTES } from "@/routes";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

export default function Navbar() {
  const navigate = useNavigate();
  const logout = useLogout();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <header className="px-6 py-3 bg-[#1e2028] flex items-center justify-between w-full box-border">
      <button className="bg-transparent text-white font-semibold px-3.5 py-2 rounded border border-[#8c2d19] cursor-pointer text-sm text-center hover:bg-[#8c2d19] transition-colors">
        Grupos
      </button>

      <div className="relative" ref={dropdownRef}>
        <button
          onClick={() => setDropdownOpen((prev) => !prev)}
          className="w-9 h-9 rounded-full border-2 border-[#8c2d19] bg-[#2a2b35] cursor-pointer flex items-center justify-center hover:border-white transition-colors"
          aria-label="Menu de perfil"
        >
          <svg className="w-5 h-5 text-[#6b6375]" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 12c2.7 0 4.8-2.1 4.8-4.8S14.7 2.4 12 2.4 7.2 4.5 7.2 7.2 9.3 12 12 12zm0 2.4c-3.2 0-9.6 1.6-9.6 4.8v2.4h19.2v-2.4c0-3.2-6.4-4.8-9.6-4.8z" />
          </svg>
        </button>

        {dropdownOpen && (
          <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-[0_4px_12px_rgba(0,0,0,0.15)] overflow-hidden z-50">
            <button
              onClick={() => {
                setDropdownOpen(false);
                void navigate(ROUTES.CHANGE_PASSWORD);
              }}
              className="w-full text-left px-4 py-2.5 text-sm text-[#08060d] bg-transparent border-none cursor-pointer hover:bg-[#f0eeeb] transition-colors"
            >
              Mudar palavra-passe
            </button>
            <div className="h-[0.5px] bg-[#e5e4e7]" />
            <button
              onClick={() => {
                setDropdownOpen(false);
                logout.mutate(undefined, {
                  onSuccess: () => void navigate(ROUTES.HOME),
                });
              }}
              className="w-full text-left px-4 py-2.5 text-sm text-[#8c2d19] bg-transparent border-none cursor-pointer hover:bg-[#8c2d19] hover:text-white transition-colors"
            >
              Terminar sessão
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
