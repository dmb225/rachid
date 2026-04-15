import { Header, Sidebar } from "@/components/layout";
import { AuthGuard } from "@/components/layout/auth-guard";
import { PageTransition } from "@/components/layout/page-transition";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <div className="flex h-screen flex-col">
        <Header />
        <Sidebar />
        <main className="flex min-h-0 flex-1 flex-col overflow-auto p-3 sm:p-6">
          <PageTransition>{children}</PageTransition>
        </main>
      </div>
    </AuthGuard>
  );
}
