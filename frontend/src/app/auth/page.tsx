// SEPEHR Frontend — Auth Pages (Login + Register)

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion } from "framer-motion";
import { useMutation } from "@tanstack/react-query";
import { useAuthStore } from "@/stores/authStore";
import { post, get } from "@/lib/api";
import type { TokenResponse, User } from "@/types";

// ── Schemas ───────────────────────────────────────────────────────────────────

const loginSchema = z.object({
  username: z.string().min(1, "نام کاربری الزامی است"),
  password: z.string().min(1, "رمز عبور الزامی است"),
});

const registerSchema = z.object({
  username: z
    .string()
    .min(3, "نام کاربری باید حداقل ۳ کاراکتر باشد")
    .max(32)
    .regex(/^[a-zA-Z0-9_]+$/, "فقط حروف انگلیسی، اعداد و _ مجاز است"),
  display_name: z.string().min(1, "نام نمایشی الزامی است").max(64),
  password: z.string().min(8, "رمز عبور باید حداقل ۸ کاراکتر باشد"),
  confirm_password: z.string(),
}).refine((d) => d.password === d.confirm_password, {
  message: "رمزهای عبور یکسان نیستند",
  path: ["confirm_password"],
});

type LoginForm = z.infer<typeof loginSchema>;
type RegisterForm = z.infer<typeof registerSchema>;

// ── Login Page ────────────────────────────────────────────────────────────────

export function LoginPage() {
  const router = useRouter();
  const { setAuth } = useAuthStore();
  const [apiError, setApiError] = useState<string | null>(null);

  const { register, handleSubmit, formState: { errors } } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  });

  const mutation = useMutation({
    mutationFn: (data: LoginForm) =>
      post<TokenResponse>("/api/v1/auth/login", data),
    onSuccess: async (tokens) => {
      const { setAccessToken, storeRefreshToken } = await import("@/lib/api");
      setAccessToken(tokens.access_token);
      storeRefreshToken(tokens.refresh_token);
      const user = await get<User>("/api/v1/auth/me");
      setAuth(user, tokens.access_token, tokens.refresh_token);
      router.replace("/home");
    },
    onError: () => {
      setApiError("نام کاربری یا رمز عبور نادرست است");
    },
  });

  const onSubmit = (data: LoginForm) => {
    setApiError(null);
    mutation.mutate(data);
  };

  return (
    <AuthLayout>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <Field
          label="نام کاربری"
          error={errors.username?.message}
          input={
            <input
              {...register("username")}
              type="text"
              placeholder="username"
              autoCapitalize="none"
              className="auth-input"
              dir="ltr"
            />
          }
        />
        <Field
          label="رمز عبور"
          error={errors.password?.message}
          input={
            <input
              {...register("password")}
              type="password"
              placeholder="••••••••"
              className="auth-input"
              dir="ltr"
            />
          }
        />

        {apiError && (
          <p className="text-sm text-danger bg-danger-muted px-3 py-2 rounded-xl">
            {apiError}
          </p>
        )}

        <motion.button
          type="submit"
          disabled={mutation.isPending}
          whileTap={{ scale: 0.97 }}
          className="w-full h-12 rounded-2xl bg-accent text-white font-semibold text-sm disabled:opacity-60 transition-all"
        >
          {mutation.isPending ? (
            <span className="flex items-center justify-center gap-2">
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              در حال ورود...
            </span>
          ) : (
            "ورود"
          )}
        </motion.button>
      </form>
    </AuthLayout>
  );
}

// ── Register Page ─────────────────────────────────────────────────────────────

export function RegisterPage() {
  const router = useRouter();
  const { setAuth } = useAuthStore();
  const [apiError, setApiError] = useState<string | null>(null);

  const { register, handleSubmit, formState: { errors } } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
  });

  const mutation = useMutation({
    mutationFn: (data: RegisterForm) =>
      post<TokenResponse>("/api/v1/auth/register", {
        username: data.username,
        password: data.password,
        display_name: data.display_name,
      }),
    onSuccess: async (tokens) => {
      const { setAccessToken, storeRefreshToken } = await import("@/lib/api");
      setAccessToken(tokens.access_token);
      storeRefreshToken(tokens.refresh_token);
      const user = await get<User>("/api/v1/auth/me");
      setAuth(user, tokens.access_token, tokens.refresh_token);
      router.replace("/home");
    },
    onError: (error: any) => {
      if (error?.response?.data?.error === "USERNAME_EXISTS") {
        setApiError("این نام کاربری قبلاً ثبت شده است");
      } else {
        setApiError("خطا در ثبت‌نام. لطفاً دوباره تلاش کنید");
      }
    },
  });

  const onSubmit = (data: RegisterForm) => {
    setApiError(null);
    mutation.mutate(data);
  };

  return (
    <AuthLayout isRegister>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <Field
          label="نام نمایشی"
          error={errors.display_name?.message}
          input={
            <input
              {...register("display_name")}
              type="text"
              placeholder="نام شما"
              className="auth-input"
            />
          }
        />
        <Field
          label="نام کاربری"
          error={errors.username?.message}
          hint="فقط حروف انگلیسی، اعداد و _ (بدون فاصله)"
          input={
            <input
              {...register("username")}
              type="text"
              placeholder="username"
              autoCapitalize="none"
              className="auth-input"
              dir="ltr"
            />
          }
        />
        <Field
          label="رمز عبور"
          error={errors.password?.message}
          input={
            <input
              {...register("password")}
              type="password"
              placeholder="حداقل ۸ کاراکتر"
              className="auth-input"
              dir="ltr"
            />
          }
        />
        <Field
          label="تکرار رمز عبور"
          error={errors.confirm_password?.message}
          input={
            <input
              {...register("confirm_password")}
              type="password"
              placeholder="••••••••"
              className="auth-input"
              dir="ltr"
            />
          }
        />

        {apiError && (
          <p className="text-sm text-danger bg-danger-muted px-3 py-2 rounded-xl">
            {apiError}
          </p>
        )}

        <motion.button
          type="submit"
          disabled={mutation.isPending}
          whileTap={{ scale: 0.97 }}
          className="w-full h-12 rounded-2xl bg-accent text-white font-semibold text-sm disabled:opacity-60"
        >
          {mutation.isPending ? (
            <span className="flex items-center justify-center gap-2">
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              در حال ثبت‌نام...
            </span>
          ) : (
            "ساخت حساب کاربری"
          )}
        </motion.button>
      </form>
    </AuthLayout>
  );
}

// ── Shared Components ─────────────────────────────────────────────────────────

function AuthLayout({
  children,
  isRegister,
}: {
  children: React.ReactNode;
  isRegister?: boolean;
}) {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-bg flex flex-col">
      {/* Background pattern */}
      <div
        className="absolute inset-0 pointer-events-none opacity-[0.03]"
        style={{
          backgroundImage: `radial-gradient(circle at 50% 0%, #4F8CFF 0%, transparent 60%)`,
        }}
      />

      <div className="flex-1 flex flex-col justify-center px-6 py-12 max-w-sm mx-auto w-full">
        {/* Logo */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-10"
        >
          <div className="w-16 h-16 rounded-3xl bg-accent/15 border border-accent/25 flex items-center justify-center mx-auto mb-4">
            <svg className="w-9 h-9 text-accent" fill="none" viewBox="0 0 24 24">
              <path
                stroke="currentColor"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2v-4M9 21H5a2 2 0 01-2-2v-4m0 0h18"
              />
            </svg>
          </div>
          <h1 className="text-2xl font-bold tracking-tight">سپهر</h1>
          <p className="text-sm text-primary-subtle mt-1">
            {isRegister ? "ایجاد حساب کاربری" : "ورود به سیستم"}
          </p>
        </motion.div>

        {/* Form */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          {children}
        </motion.div>

        {/* Switch */}
        <p className="text-center text-sm text-primary-subtle mt-6">
          {isRegister ? (
            <>
              حساب دارید؟{" "}
              <button
                onClick={() => router.push("/auth/login")}
                className="text-accent font-medium"
              >
                وارد شوید
              </button>
            </>
          ) : (
            <>
              حساب ندارید؟{" "}
              <button
                onClick={() => router.push("/auth/register")}
                className="text-accent font-medium"
              >
                ثبت‌نام کنید
              </button>
            </>
          )}
        </p>
      </div>

      <style jsx global>{`
        .auth-input {
          width: 100%;
          background: #1C2330;
          border: 1px solid rgba(255,255,255,0.08);
          border-radius: 14px;
          padding: 12px 16px;
          color: #FFFFFF;
          font-size: 14px;
          outline: none;
          transition: border-color 0.2s;
        }
        .auth-input:focus {
          border-color: rgba(79,140,255,0.5);
        }
        .auth-input::placeholder {
          color: rgba(185,192,204,0.35);
        }
      `}</style>
    </div>
  );
}

function Field({
  label,
  error,
  hint,
  input,
}: {
  label: string;
  error?: string;
  hint?: string;
  input: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label className="text-sm font-medium text-primary-muted">{label}</label>
      {input}
      {hint && !error && <p className="text-xs text-primary-subtle">{hint}</p>}
      {error && <p className="text-xs text-danger">{error}</p>}
    </div>
  );
}
