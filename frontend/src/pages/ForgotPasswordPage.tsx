import { api } from "@/api/client";
import { ApiError } from "@/types/api";
import AuthPageLayout from "@/components/auth/AuthPageLayout";
import BackLink from "@/components/auth/BackLink";
import FormCard from "@/components/auth/FormCard";
import FormField from "@/components/auth/FormField";
import SubmitButton from "@/components/auth/SubmitButton";
import useShake from "@/components/auth/useShake";
import { ROUTES } from "@/routes";
import { useState } from "react";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");
  const { shake, isShaking } = useShake<"email">();

  const handleSubmit = (e: React.SyntheticEvent) => {
    e.preventDefault();
    setError("");

    if (!email) {
      setError("Preencha este campo.");
      shake("email");
      return;
    }

    setLoading(true);
    api
      .post("/api/auth/forgot-password", { email })
      .then(() => {
        setSubmitted(true);
      })
      .catch((err: { code?: string }) => {
        if (err.code === ApiError.AUTH_ALREADY_AUTHENTICATED) {
          setError("Já tem sessão iniciada.");
        } else {
          setError("Ocorreu um erro. Tente novamente mais tarde.");
        }
        shake("email");
      })
      .finally(() => {
        setLoading(false);
      });
  };

  return (
    <AuthPageLayout>
      <FormCard onSubmit={submitted ? undefined : handleSubmit}>
        <h1 className="text-[#08060d] text-2xl font-bold m-0">Recuperar palavra-passe</h1>

        {submitted ? (
          <>
            <p className="text-[#6b6375] text-sm leading-normal m-0">
              Se o e-mail introduzido estiver associado a uma conta, receberá uma mensagem com
              instruções para redefinir a sua palavra-passe.
            </p>
            <BackLink to={ROUTES.LOGIN}>Voltar ao início de sessão</BackLink>
          </>
        ) : (
          <>
            <p className="text-[#6b6375] text-sm leading-normal m-0">
              Introduza o seu e-mail e enviaremos instruções para redefinir a sua palavra-passe.
            </p>

            <FormField
              id="email"
              label="E-mail"
              type="email"
              placeholder="exemplo@mail.com"
              value={email}
              onChange={setEmail}
              error={error}
              shake={isShaking("email")}
            />

            <SubmitButton loading={loading} label="Enviar e-mail" loadingLabel="A enviar..." />
            <BackLink to={ROUTES.LOGIN}>Voltar ao início de sessão</BackLink>
          </>
        )}
      </FormCard>
    </AuthPageLayout>
  );
}
