import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useChangePassword } from "@/api/hooks/useAuth";
import AuthPageLayout from "@/components/auth/AuthPageLayout";
import BackLink from "@/components/auth/BackLink";
import FormCard from "@/components/auth/FormCard";
import PasswordField from "@/components/auth/PasswordField";
import PasswordStrength from "@/components/auth/PasswordStrength";
import SubmitButton from "@/components/auth/SubmitButton";
import useShake from "@/components/auth/useShake";
import { ROUTES } from "@/routes";
import { ApiError } from "@/types/api";

type Field = "oldPassword" | "newPassword" | "confirmPassword";

export default function ChangePasswordPage() {
  const navigate = useNavigate();

  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [errors, setErrors] = useState<Partial<Record<Field, string>>>({});
  const [countdown, setCountdown] = useState<number | null>(null);

  const oldPasswordRef = useRef<HTMLInputElement>(null);
  const newPasswordRef = useRef<HTMLInputElement>(null);
  const confirmPasswordRef = useRef<HTMLInputElement>(null);

  const changePassword = useChangePassword();
  const { shake, isShaking } = useShake<Field>();

  useEffect(() => {
    if (!changePassword.isPending && changePassword.isError) {
      if (errors.newPassword) newPasswordRef.current?.focus();
      else oldPasswordRef.current?.focus();
    }
  }, [changePassword.isPending, changePassword.isError, errors.newPassword]);

  useEffect(() => {
    if (countdown === null) return;
    if (countdown <= 0) {
      void navigate(ROUTES.HOME);
      return;
    }
    const timer = setTimeout(() => setCountdown((c) => (c ?? 1) - 1), 1000);
    return () => clearTimeout(timer);
  }, [countdown, navigate]);

  const setFieldError = (field: Field, message: string) => {
    setErrors({ [field]: message });
    shake(field);
  };

  const clearFieldError = (field: Field) => {
    setErrors((prev) => {
      const next = { ...prev };
      delete next[field];
      return next;
    });
  };

  const validateNewPassword = (): boolean => {
    if (!newPassword) {
      setFieldError("newPassword", "Preencha este campo.");
      return false;
    }
    if (newPassword.length < 8) {
      setFieldError("newPassword", "A palavra-passe deve ter pelo menos 8 caracteres.");
      return false;
    }
    if (!/[a-z]/.test(newPassword) || !/[A-Z]/.test(newPassword)) {
      setFieldError("newPassword", "Deve ter pelo menos uma letra maiúscula e uma minúscula.");
      return false;
    }
    if (!/\d/.test(newPassword)) {
      setFieldError("newPassword", "Deve ter pelo menos um número.");
      return false;
    }
    if (!/[!@#$%^&*]/.test(newPassword)) {
      setFieldError("newPassword", "Deve ter pelo menos um caractere especial (!@#$%^&*).");
      return false;
    }
    clearFieldError("newPassword");
    return true;
  };

  const validateConfirmPassword = (): boolean => {
    if (!confirmPassword) {
      setFieldError("confirmPassword", "Preencha este campo.");
      return false;
    }
    if (newPassword !== confirmPassword) {
      setFieldError("confirmPassword", "As palavras-passe não coincidem.");
      return false;
    }
    clearFieldError("confirmPassword");
    return true;
  };

  const validateOldPassword = (): boolean => {
    if (!oldPassword) {
      setFieldError("oldPassword", "Preencha este campo.");
      return false;
    }
    clearFieldError("oldPassword");
    return true;
  };

  const handleKeyDown = (field: "new" | "confirm" | "old") => (e: React.KeyboardEvent) => {
    if (e.key !== "Enter") return;
    e.preventDefault();
    if (field === "new") {
      if (validateNewPassword()) confirmPasswordRef.current?.focus();
    } else if (field === "confirm") {
      if (validateConfirmPassword()) oldPasswordRef.current?.focus();
    } else {
      if (validateOldPassword()) oldPasswordRef.current?.closest("form")?.requestSubmit();
    }
  };

  const handleSubmit = (e: React.SyntheticEvent) => {
    e.preventDefault();
    setErrors({});

    if (!validateNewPassword()) return;
    if (!validateConfirmPassword()) return;
    if (!validateOldPassword()) return;

    changePassword.mutate(
      { old_password: oldPassword, new_password: newPassword },
      {
        onSuccess: () => {
          setCountdown(3);
        },
        onError: (err) => {
          if (err.code === ApiError.AUTH_INVALID_OLD_PASSWORD) {
            setFieldError("oldPassword", "Palavra-passe antiga incorreta.");
          } else if (err.code === ApiError.AUTH_PASSWORD_POLICY_VIOLATION) {
            setFieldError(
              "newPassword",
              err.apiMessage ?? "A palavra-passe não cumpre os requisitos de segurança.",
            );
          } else {
            setFieldError("oldPassword", "Ocorreu um erro. Tente novamente.");
          }
        },
      },
    );
  };

  if (countdown !== null) {
    return (
      <AuthPageLayout>
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
      </AuthPageLayout>
    );
  }

  return (
    <AuthPageLayout>
      <FormCard onSubmit={handleSubmit}>
        <h1 className="text-[#08060d] text-2xl font-bold m-0">Mudar palavra-passe</h1>

        <PasswordField
          ref={newPasswordRef}
          id="new-password"
          label="Palavra-passe nova"
          value={newPassword}
          onChange={setNewPassword}
          onKeyDown={handleKeyDown("new")}
          error={errors.newPassword}
          shake={isShaking("newPassword")}
          disabled={changePassword.isPending}
        >
          <PasswordStrength password={newPassword} />
        </PasswordField>

        <PasswordField
          ref={confirmPasswordRef}
          id="confirm-password"
          label="Confirmação da palavra-passe nova"
          value={confirmPassword}
          onChange={setConfirmPassword}
          onKeyDown={handleKeyDown("confirm")}
          error={errors.confirmPassword}
          shake={isShaking("confirmPassword")}
          disabled={changePassword.isPending}
        />

        <PasswordField
          ref={oldPasswordRef}
          id="old-password"
          label="Palavra-passe antiga"
          value={oldPassword}
          onChange={setOldPassword}
          onKeyDown={handleKeyDown("old")}
          error={errors.oldPassword}
          shake={isShaking("oldPassword")}
          disabled={changePassword.isPending}
        />

        <SubmitButton
          loading={changePassword.isPending}
          label="Guardar mudanças"
          loadingLabel="A guardar..."
        />
        <BackLink to={ROUTES.HOME}>Voltar à página inicial</BackLink>
      </FormCard>
    </AuthPageLayout>
  );
}
