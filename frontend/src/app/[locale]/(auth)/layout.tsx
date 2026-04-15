import Link from "next/link";
import { ThemeToggle } from "@/components/theme";
import { APP_NAME, APP_DESCRIPTION, ROUTES } from "@/lib/constants";
import { Bot, MessageSquare, Database, Shield, Zap, Lock } from "lucide-react";

const features = [
  { icon: MessageSquare, label: "AI Chat" },
  { icon: Database, label: "Knowledge Base" },
  { icon: Shield, label: "Secure Auth" },
  { icon: Zap, label: "Real-time" },
];

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="bg-background min-h-screen lg:grid lg:grid-cols-2">
      {/* Left — hero panel (desktop only) */}
      <div className="relative hidden flex-col justify-between overflow-hidden bg-zinc-100 p-10 lg:flex dark:bg-zinc-950">
        <div className="pointer-events-none absolute inset-0">
          <div className="grid-bg absolute inset-0 opacity-30 dark:opacity-60" />
          <div className="bg-brand/[0.08] dark:bg-brand/[0.15] absolute top-1/2 left-1/2 h-[600px] w-[600px] -translate-x-1/2 -translate-y-1/2 rounded-full blur-[150px]" />
          <div className="bg-brand/[0.05] dark:bg-brand/[0.08] absolute top-0 right-0 h-[300px] w-[400px] rounded-full blur-[120px]" />
        </div>

        <div className="relative z-10">
          <Link href={ROUTES.HOME} className="flex items-center gap-2">
            <div className="bg-brand flex h-8 w-8 items-center justify-center rounded-lg">
              <Lock className="h-4 w-4 text-white" />
            </div>
            <span className="text-lg font-bold text-zinc-900 dark:text-white">{APP_NAME}</span>
          </Link>
        </div>

        <div className="relative z-10">
          <div className="mb-6 inline-flex items-center rounded-full border border-zinc-200 bg-zinc-200/50 px-3 py-1 text-sm text-zinc-500 dark:border-white/10 dark:bg-white/5 dark:text-zinc-400">
            <Bot className="text-brand mr-2 h-3.5 w-3.5" />
            {APP_DESCRIPTION}
          </div>
          <h1 className="mb-4 text-4xl leading-tight font-bold tracking-tight text-zinc-900 xl:text-5xl dark:text-white">
            Build intelligent{" "}
            <span className="from-brand to-brand-hover bg-gradient-to-r bg-clip-text text-transparent">
              applications
            </span>{" "}
            faster.
          </h1>
          <p className="max-w-md text-lg leading-relaxed text-zinc-500 dark:text-zinc-400">
            Production-ready platform with AI agents, vector search, and enterprise-grade
            authentication.
          </p>

          {features.length > 0 && (
            <div className="mt-8 flex flex-wrap gap-3">
              {features.map((f) => (
                <div
                  key={f.label}
                  className="flex items-center gap-2 rounded-full border border-zinc-200 bg-zinc-200/50 px-4 py-2 text-sm text-zinc-600 dark:border-white/10 dark:bg-white/5 dark:text-zinc-300"
                >
                  <f.icon className="text-brand h-4 w-4" />
                  {f.label}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="relative z-10">
          <blockquote className="border-brand/40 border-l-2 pl-4">
            <p className="text-sm leading-relaxed text-zinc-400 italic dark:text-zinc-500">
              &ldquo;Ship AI-powered apps in days, not months. Everything you need from auth to RAG,
              pre-configured and ready to deploy.&rdquo;
            </p>
          </blockquote>
        </div>
      </div>

      {/* Right — form (contrasting background) */}
      <div className="flex flex-col bg-zinc-50 dark:bg-zinc-900/50">
        <div className="flex h-14 items-center justify-between px-4 sm:px-8">
          <Link href={ROUTES.HOME} className="text-lg font-bold tracking-tight lg:hidden">
            {APP_NAME}
          </Link>
          <div className="ml-auto">
            <ThemeToggle />
          </div>
        </div>

        <div className="flex flex-1 items-center justify-center px-4 py-8 sm:px-8">
          <div className="w-full max-w-md">{children}</div>
        </div>
      </div>
    </div>
  );
}
