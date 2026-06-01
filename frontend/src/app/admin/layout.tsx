"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { BarChart2, LogOut, ShieldCheck, LayoutDashboard } from "lucide-react";
import { adminApi } from "@/lib/api";
import type { User } from "@/lib/types";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [admin, setAdmin] = useState<User | null>(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    // Admin pages (except login) require admin token
    if (pathname === "/admin/login") {
      setChecking(false);
      return;
    }
    const token = localStorage.getItem("portai_admin_token");
    if (!token) {
      router.replace("/admin/login");
      return;
    }
    adminApi
      .me()
      .then((me) => {
        if (me.role !== "admin") {
          localStorage.removeItem("portai_admin_token");
          router.replace("/admin/login");
        } else {
          setAdmin(me);
        }
      })
      .catch(() => {
        localStorage.removeItem("portai_admin_token");
        router.replace("/admin/login");
      })
      .finally(() => {
        setChecking(false);
      });
  }, [pathname, router]);

  function handleLogout() {
    localStorage.removeItem("portai_admin_token");
    router.push("/admin/login");
  }

  // Login page: no layout wrapper
  if (pathname === "/admin/login") return <>{children}</>;

  if (checking) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!admin) return null;

  const navItems = [
    { href: "/admin/dashboard", label: "Dashboard", icon: LayoutDashboard },
  ];

  return (
    <div className="flex min-h-screen bg-gray-950">
      {/* Sidebar */}
      <aside className="fixed left-0 top-0 h-full w-56 bg-gray-900 border-r border-gray-800 flex flex-col">
        {/* Logo */}
        <div className="px-5 py-5 border-b border-gray-800">
          <div className="flex items-center gap-2 mb-0.5">
            <BarChart2 className="text-indigo-400" size={18} />
            <span className="font-bold text-white text-sm">PortAI</span>
          </div>
          <div className="flex items-center gap-1.5 mt-1">
            <ShieldCheck size={13} className="text-indigo-400" />
            <span className="text-xs text-indigo-400 font-medium">Admin Panel</span>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition ${
                  active
                    ? "bg-indigo-600 text-white"
                    : "text-gray-400 hover:bg-gray-800 hover:text-white"
                }`}
              >
                <Icon size={16} />
                {label}
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="px-3 py-4 border-t border-gray-800">
          <div className="px-3 py-2 mb-2">
            <p className="text-xs font-medium text-white truncate">{admin.name}</p>
            <p className="text-xs text-gray-500 truncate">{admin.email}</p>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm text-gray-400 hover:bg-gray-800 hover:text-red-400 transition"
          >
            <LogOut size={15} />
            Logout
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 ml-56 p-8 text-white">
        {children}
      </main>
    </div>
  );
}
