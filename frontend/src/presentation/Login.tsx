import { z } from "zod";
import { useState } from "react";

import CredentialForm from "@/components/credential-form/CredentialForm";
import SlideInEffect from "@/animations/slide-in/SlideInEffect";

import style from "./style.module.css";

import { useAuthStore } from "@/store/useAuthStore";
import type { LoginCredentials } from "@/store/schemas";
import { LoginCredentialsSchema } from "@/store/schemas";

export default function LoginPage() {
  const { login, isAuthenticated, showToast } = useAuthStore();

  const [validating, setValidating] = useState(false);
  const [credentials, setCredentials] = useState<LoginCredentials>({
    username: "",
    password: "",
  });

  const handleLogin = async () => {
    setValidating(true);
    try {
      LoginCredentialsSchema.parse(credentials);
      await login({
        username: credentials.username,
        password: credentials.password,
      })
        .then(() => {
          showToast(`Bem vindo de volta!`, "success");
        })
        .catch((error) => {
          showToast(
            error instanceof Error ? error.message : "Falha no login.",
            "error",
          );
        })
        .finally(() => {
          setValidating(false);
        });
    } catch (error) {
      if (error instanceof z.ZodError) {
        showToast(
          error.issues.map((issue) => issue.message).join(", "),
          "error",
        );
        setValidating(false);
        return;
      }
      showToast("Tivemos um problema inesperado.", "error");
      setValidating(false);
    }
  };

  return (
    <SlideInEffect duration={0.5}>
      {isAuthenticated ? (
        <div>User</div>
      ) : (
        <>
          <div className={style.container}>
            <form
              className={style.main}
              onSubmit={(e) => {
                e.preventDefault();
                handleLogin();
              }}
            >
              <span className={style.subtitle}>Informe suas credenciais</span>
              <CredentialForm
                id="username"
                type="text"
                label="Usuário"
                value={credentials.username}
                autoFocus
                onChange={(value) =>
                  setCredentials({ ...credentials, username: value })
                }
              />
              <CredentialForm
                id="password"
                type="password"
                label="Senha"
                value={credentials.password}
                onChange={(value) =>
                  setCredentials({ ...credentials, password: value })
                }
              />
              <button type="submit" className={style.btn} disabled={validating}>
                Entrar
              </button>
              <span className={style.support}>
                Em caso de dúvidas, contate o suporte.
              </span>
            </form>
          </div>
        </>
      )}
    </SlideInEffect>
  );
}
