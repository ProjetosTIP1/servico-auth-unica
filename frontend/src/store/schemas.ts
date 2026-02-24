import { z } from "zod";

export const ColaboradorSchema = z.object({
    id: z.string(),
    nome: z.string(),
    email: z.string(),
    cargo: z.string(),
    departamento: z.string(),
});

export const LoginCredentialsSchema = z.object({
    username: z.string().min(1, "Usuário obrigatório"),
    password: z.string().min(1, "Senha obrigatória"),
});

export type Colaborador = z.infer<typeof ColaboradorSchema>;
export type LoginCredentials = z.infer<typeof LoginCredentialsSchema>;