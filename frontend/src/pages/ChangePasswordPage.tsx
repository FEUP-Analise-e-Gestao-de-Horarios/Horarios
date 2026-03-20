import { api } from "@/api/client";
import { ROUTES } from "@/routes";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

function getPasswordStrength(password: string): { score: number; label: string; color: string } {
  let score = 0;
  if (password.length >= 8) score++;
  if (password.length >= 12) score++;
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++;
  if (/\d/.test(password)) score++;
  if (/[!@#$%^&*]/.test(password)) score++;

  if (score <= 1) return { score, label: "Fraca", color: "#dc2626" };
  if (score <= 2) return { score, label: "Razoável", color: "#f97316" };
  if (score <= 3) return { score, label: "Média", color: "#eab308" };
  if (score <= 4) return { score, label: "Forte", color: "#22c55e" };
  return { score, label: "Muito forte", color: "#16a34a" };
}

type FieldErrors = {
  oldPassword?: string;
  newPassword?: string;
  confirmPassword?: string;
};

export default function ChangePasswordPage() {
  const navigate = useNavigate();
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [errors, setErrors] = useState<FieldErrors>({});
  const [shakeField, setShakeField] = useState<keyof FieldErrors | null>(null);
  const [countdown, setCountdown] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [showOld, setShowOld] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const strength = useMemo(() => getPasswordStrength(newPassword), [newPassword]);
  const oldPasswordRef = useRef<HTMLInputElement>(null);
  const newPasswordRef = useRef<HTMLInputElement>(null);
  const confirmPasswordRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (countdown === null) return;
    if (countdown <= 0) {
      void navigate(ROUTES.HOME);
      return;
    }
    const timer = setTimeout(() => setCountdown((c) => (c ?? 1) - 1), 1000);
    return () => clearTimeout(timer);
  }, [countdown, navigate]);

  const shake = (field: keyof FieldErrors) => {
    setShakeField(field);
    setTimeout(() => setShakeField(null), 500);
  };

  const validateOldPassword = (): boolean => {
    if (!oldPassword) {
      setErrors({ oldPassword: "Preencha este campo." });
      shake("oldPassword");
      return false;
    }
    setErrors((prev) => {
      const { oldPassword: _old, ...rest } = prev;
      void _old;
      return rest;
    });
    return true;
  };

  const validateNewPassword = (): boolean => {
    if (!newPassword) {
      setErrors({ newPassword: "Preencha este campo." });
      shake("newPassword");
      return false;
    }
    if (newPassword.length < 8) {
      setErrors({ newPassword: "A palavra-passe deve ter pelo menos 8 caracteres." });
      shake("newPassword");
      return false;
    }
    if (!/[a-z]/.test(newPassword) || !/[A-Z]/.test(newPassword)) {
      setErrors({ newPassword: "Deve ter pelo menos uma letra maiúscula e uma minúscula." });
      shake("newPassword");
      return false;
    }
    if (!/\d/.test(newPassword)) {
      setErrors({ newPassword: "Deve ter pelo menos um número." });
      shake("newPassword");
      return false;
    }
    if (!/[!@#$%^&*]/.test(newPassword)) {
      setErrors({ newPassword: "Deve ter pelo menos um caractere especial (!@#$%^&*)." });
      shake("newPassword");
      return false;
    }
    setErrors((prev) => {
      const { newPassword: _new, ...rest } = prev;
      void _new;
      return rest;
    });
    return true;
  };

  const validateConfirmPassword = (): boolean => {
    if (!confirmPassword) {
      setErrors({ confirmPassword: "Preencha este campo." });
      shake("confirmPassword");
      return false;
    }
    if (newPassword !== confirmPassword) {
      setErrors({ confirmPassword: "As palavras-passe não coincidem." });
      shake("confirmPassword");
      return false;
    }
    setErrors((prev) => {
      const { confirmPassword: _confirm, ...rest } = prev;
      void _confirm;
      return rest;
    });
    return true;
  };

  const handleKeyDown = (field: "old" | "new" | "confirm") => (e: React.KeyboardEvent) => {
    if (e.key !== "Enter") return;
    e.preventDefault();
    if (field === "old") {
      if (validateOldPassword()) newPasswordRef.current?.focus();
    } else if (field === "new") {
      if (validateNewPassword()) confirmPasswordRef.current?.focus();
    } else {
      if (validateConfirmPassword()) {
        const form = confirmPasswordRef.current?.closest("form");
        form?.requestSubmit();
      }
    }
  };

  const handleSubmit = (e: React.SyntheticEvent) => {
    e.preventDefault();
    setErrors({});

    if (!oldPassword) {
      setErrors({ oldPassword: "Preencha este campo." });
      shake("oldPassword");
      return;
    }

    if (!newPassword) {
      setErrors({ newPassword: "Preencha este campo." });
      shake("newPassword");
      return;
    }

    if (newPassword.length < 8) {
      setErrors({ newPassword: "A palavra-passe deve ter pelo menos 8 caracteres." });
      shake("newPassword");
      return;
    }

    if (!/[a-z]/.test(newPassword) || !/[A-Z]/.test(newPassword)) {
      setErrors({ newPassword: "Deve ter pelo menos uma letra maiúscula e uma minúscula." });
      shake("newPassword");
      return;
    }

    if (!/\d/.test(newPassword)) {
      setErrors({ newPassword: "Deve ter pelo menos um número." });
      shake("newPassword");
      return;
    }

    if (!/[!@#$%^&*]/.test(newPassword)) {
      setErrors({ newPassword: "Deve ter pelo menos um caractere especial (!@#$%^&*)." });
      shake("newPassword");
      return;
    }

    if (!confirmPassword) {
      setErrors({ confirmPassword: "Preencha este campo." });
      shake("confirmPassword");
      return;
    }

    if (newPassword !== confirmPassword) {
      setErrors({ confirmPassword: "As palavras-passe não coincidem." });
      shake("confirmPassword");
      return;
    }

    setLoading(true);
    api
      .post("/api/auth/change_password", {
        old_password: oldPassword,
        new_password: newPassword,
      })
      .then(() => {
        setCountdown(3);
      })
      .catch(() => {
        setErrors({ oldPassword: "Palavra-passe antiga incorreta." });
        shake("oldPassword");
      })
      .finally(() => {
        setLoading(false);
      });
  };

  const fieldClass = (field: keyof FieldErrors) =>
    `w-full px-3 py-2 pr-10 rounded border outline-none bg-[#f4f3ec] text-[#08060d] focus:border-[rgba(140,45,25,0.5)] focus:ring-1 focus:ring-[rgba(140,45,25,0.5)] placeholder:text-[#c5c1ca] ${
      errors[field] ? "border-[#8c2d19]" : "border-[#e5e4e7]"
    }`;

  const shakeClass = (field: keyof FieldErrors) => (shakeField === field ? "animate-shake" : "");

  if (countdown !== null) {
    return (
      <div className="min-h-svh bg-white flex items-center justify-center font-[system-ui,'Segoe_UI',Roboto,sans-serif] text-[#6b6375] text-lg leading-[145%] tracking-[0.18px] antialiased max-lg:text-base">
        <div className="flex flex-col items-center gap-5 w-96 p-8">
          <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center">
            <svg
              className="w-8 h-8 text-green-600"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2.5}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="text-[#08060d] text-xl font-bold m-0">Palavra-passe alterada!</h2>
          <p className="text-[#6b6375] text-sm m-0 text-center">
            A redirecionar em {countdown}s...
          </p>
          <div className="w-full h-1.5 rounded-full bg-[#e5e4e7] overflow-hidden">
            <div
              className="h-full bg-green-500 rounded-full transition-all duration-1000 ease-linear"
              style={{ width: `${(countdown / 3) * 100}%` }}
            />
          </div>
        </div>
      </div>
    );
  }

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
      <form
        onSubmit={handleSubmit}
        className="flex flex-col gap-5 w-96 p-8 rounded-lg shadow-[rgba(0,0,0,0.1)_0_10px_15px_-3px,rgba(0,0,0,0.05)_0_4px_6px_-2px] border border-[#e5e4e7]"
      >
        <h1 className="text-[#08060d] text-2xl font-bold m-0">Mudar palavra-passe</h1>

        <div className={`flex flex-col gap-1.5 ${shakeClass("oldPassword")}`}>
          <label htmlFor="old-password" className="text-sm text-[#6b6375]">
            Palavra-passe antiga
          </label>
          <div className="relative">
            <input
              ref={oldPasswordRef}
              id="old-password"
              type={showOld ? "text" : "password"}
              placeholder="••••••••"
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              onKeyDown={handleKeyDown("old")}
              className={fieldClass("oldPassword")}
            />
            <button
              type="button"
              onClick={() => setShowOld((v) => !v)}
              className="absolute right-2 top-1/2 -translate-y-1/2 bg-transparent border-none cursor-pointer text-[#9b95a3] hover:text-[#08060d] text-sm p-0.5"
            >
              {showOld ? "Ocultar" : "Mostrar"}
            </button>
          </div>
          {errors.oldPassword && (
            <p className="text-[#8c2d19] text-[13px] m-0">{errors.oldPassword}</p>
          )}
        </div>

        <div className={`flex flex-col gap-1.5 ${shakeClass("newPassword")}`}>
          <label htmlFor="new-password" className="text-sm text-[#6b6375]">
            Palavra-passe nova
          </label>
          <div className="relative">
            <input
              ref={newPasswordRef}
              id="new-password"
              type={showNew ? "text" : "password"}
              placeholder="••••••••"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              onKeyDown={handleKeyDown("new")}
              className={fieldClass("newPassword")}
            />
            <button
              type="button"
              onClick={() => setShowNew((v) => !v)}
              className="absolute right-2 top-1/2 -translate-y-1/2 bg-transparent border-none cursor-pointer text-[#9b95a3] hover:text-[#08060d] text-sm p-0.5"
            >
              {showNew ? "Ocultar" : "Mostrar"}
            </button>
          </div>
          {errors.newPassword && (
            <p className="text-[#8c2d19] text-[13px] m-0">{errors.newPassword}</p>
          )}
          {newPassword && (
            <div className="flex flex-col gap-1.5 mt-1">
              <div className="flex gap-1">
                {Array.from({ length: 5 }, (_, i) => (
                  <div
                    key={i}
                    className="h-1.5 flex-1 rounded-full transition-colors"
                    style={{
                      backgroundColor: i < strength.score ? strength.color : "#e5e4e7",
                    }}
                  />
                ))}
              </div>
              <span className="text-[13px]" style={{ color: strength.color }}>
                {strength.label}
              </span>
            </div>
          )}
          <div className="flex flex-col gap-1 text-[12px] text-[#9b95a3] mt-1">
            <span className={newPassword.length >= 8 ? "text-green-500 font-medium" : ""}>
              Pelo menos 8 caracteres
            </span>
            <span
              className={
                /[a-z]/.test(newPassword) && /[A-Z]/.test(newPassword)
                  ? "text-green-500 font-medium"
                  : ""
              }
            >
              Uma letra maiúscula e uma minúscula
            </span>
            <span className={/\d/.test(newPassword) ? "text-green-500 font-medium" : ""}>
              Pelo menos um número
            </span>
            <span className={/[!@#$%^&*]/.test(newPassword) ? "text-green-500 font-medium" : ""}>
              Pelo menos um caractere especial (!@#$%^&*)
            </span>
          </div>
        </div>

        <div className={`flex flex-col gap-1.5 ${shakeClass("confirmPassword")}`}>
          <label htmlFor="confirm-password" className="text-sm text-[#6b6375]">
            Confirmação da palavra-passe nova
          </label>
          <div className="relative">
            <input
              ref={confirmPasswordRef}
              id="confirm-password"
              type={showConfirm ? "text" : "password"}
              placeholder="••••••••"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              onKeyDown={handleKeyDown("confirm")}
              className={fieldClass("confirmPassword")}
            />
            <button
              type="button"
              onClick={() => setShowConfirm((v) => !v)}
              className="absolute right-2 top-1/2 -translate-y-1/2 bg-transparent border-none cursor-pointer text-[#9b95a3] hover:text-[#08060d] text-sm p-0.5"
            >
              {showConfirm ? "Ocultar" : "Mostrar"}
            </button>
          </div>
          {errors.confirmPassword && (
            <p className="text-[#8c2d19] text-[13px] m-0">{errors.confirmPassword}</p>
          )}
        </div>

        <button
          type="submit"
          disabled={loading}
          className="bg-[#8c2d19] text-white font-semibold py-2.5 rounded border-none cursor-pointer text-[15px] hover:bg-[#722415] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? "A guardar..." : "Guardar mudanças"}
        </button>
        <Link
          to={ROUTES.HOME}
          className="text-[#9b95a3] text-sm text-center no-underline hover:text-[#08060d] transition-colors flex items-center justify-center gap-1.5"
        >
          <span aria-hidden="true">&larr;</span> Voltar à página inicial
        </Link>
      </form>
    </div>
  );
}
