import { useMemo } from "react";

function getStrength(password: string): { score: number; label: string; color: string } {
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

export default function PasswordStrength({ password }: { password: string }) {
  const strength = useMemo(() => getStrength(password), [password]);

  return (
    <>
      {password && (
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
        <span className={password.length >= 8 ? "text-green-500 font-medium" : ""}>
          Pelo menos 8 caracteres
        </span>
        <span
          className={
            /[a-z]/.test(password) && /[A-Z]/.test(password) ? "text-green-500 font-medium" : ""
          }
        >
          Uma letra maiúscula e uma minúscula
        </span>
        <span className={/\d/.test(password) ? "text-green-500 font-medium" : ""}>
          Pelo menos um número
        </span>
        <span className={/[!@#$%^&*]/.test(password) ? "text-green-500 font-medium" : ""}>
          Pelo menos um caractere especial (!@#$%^&*)
        </span>
      </div>
    </>
  );
}
