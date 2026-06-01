"use client";

import { useEffect, useState } from "react";
import { Users, BarChart2, ShieldCheck, RefreshCw, UserCheck, User as UserIcon } from "lucide-react";
import { adminApi } from "@/lib/api";
import type { AdminUserItem } from "@/lib/types";

function RoleBadge({ role }: { role: string }) {
  return role === "admin" ? (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-indigo-900 text-indigo-300 border border-indigo-700">
      <ShieldCheck size={11} /> Admin
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-gray-800 text-gray-400 border border-gray-700">
      <UserIcon size={11} /> User
    </span>
  );
}

function StatCard({ label, value, icon: Icon, color }: {
  label: string;
  value: number | string;
  icon: React.ElementType;
  color: string;
}) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm text-gray-400">{label}</span>
        <div className={`p-2 rounded-lg ${color}`}>
          <Icon size={16} className="text-white" />
        </div>
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
    </div>
  );
}

export default function AdminDashboardPage() {
  const [users, setUsers] = useState<AdminUserItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [updatingId, setUpdatingId] = useState<number | null>(null);

  async function fetchUsers() {
    setLoading(true);
    try {
      const data = await adminApi.users();
      setUsers(data);
    } catch {
      // token issues handled by layout guard
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { fetchUsers(); }, []);

  async function toggleRole(user: AdminUserItem) {
    setUpdatingId(user.id);
    try {
      const newRole = user.role === "admin" ? "user" : "admin";
      await adminApi.updateRole(user.id, newRole);
      setUsers((prev) => prev.map((u) => u.id === user.id ? { ...u, role: newRole as "user" | "admin" } : u));
    } catch {
      alert("Failed to update role.");
    } finally {
      setUpdatingId(null);
    }
  }

  const filtered = users.filter(
    (u) =>
      u.name.toLowerCase().includes(search.toLowerCase()) ||
      u.email.toLowerCase().includes(search.toLowerCase())
  );

  const totalUsers = users.length;
  const adminCount = users.filter((u) => u.role === "admin").length;
  const totalPortfolios = users.reduce((s, u) => s + u.portfolio_count, 0);

  return (
    <div className="max-w-6xl">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="text-gray-500 text-sm mt-1">Manage all registered accounts</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <StatCard label="Total Users" value={totalUsers} icon={Users} color="bg-indigo-600" />
        <StatCard label="Admin Accounts" value={adminCount} icon={ShieldCheck} color="bg-violet-600" />
        <StatCard label="Total Portfolios" value={totalPortfolios} icon={BarChart2} color="bg-emerald-600" />
      </div>

      {/* Table */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        {/* Table header */}
        <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white flex items-center gap-2">
            <Users size={16} className="text-indigo-400" />
            Registered Accounts
          </h2>
          <div className="flex items-center gap-3">
            <input
              type="text"
              placeholder="Search name or email…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="bg-gray-800 border border-gray-700 text-white text-sm rounded-lg px-3 py-1.5 w-52 placeholder-gray-600 focus:outline-none focus:border-indigo-500"
            />
            <button
              onClick={fetchUsers}
              disabled={loading}
              className="p-1.5 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-white transition"
              title="Refresh"
            >
              <RefreshCw size={15} className={loading ? "animate-spin" : ""} />
            </button>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16 text-gray-500 gap-2">
            <RefreshCw size={16} className="animate-spin" />
            <span className="text-sm">Loading users…</span>
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-16 text-gray-600 text-sm">
            No users found.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-gray-500 text-xs uppercase tracking-wider">
                <th className="px-6 py-3 text-left font-medium">ID</th>
                <th className="px-6 py-3 text-left font-medium">Name</th>
                <th className="px-6 py-3 text-left font-medium">Email</th>
                <th className="px-6 py-3 text-left font-medium">Role</th>
                <th className="px-6 py-3 text-left font-medium">Risk Profile</th>
                <th className="px-6 py-3 text-left font-medium">Portfolios</th>
                <th className="px-6 py-3 text-left font-medium">Joined</th>
                <th className="px-6 py-3 text-left font-medium">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {filtered.map((user) => (
                <tr key={user.id} className="hover:bg-gray-800/50 transition">
                  <td className="px-6 py-3 text-gray-500 font-mono text-xs">#{user.id}</td>
                  <td className="px-6 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-full bg-indigo-900 flex items-center justify-center text-indigo-300 text-xs font-bold flex-shrink-0">
                        {user.name.charAt(0).toUpperCase()}
                      </div>
                      <span className="text-white font-medium truncate max-w-[120px]">{user.name}</span>
                    </div>
                  </td>
                  <td className="px-6 py-3 text-gray-400 truncate max-w-[180px]">{user.email}</td>
                  <td className="px-6 py-3"><RoleBadge role={user.role} /></td>
                  <td className="px-6 py-3 text-gray-400 capitalize">
                    {user.risk_tolerance ?? <span className="text-gray-700">—</span>}
                  </td>
                  <td className="px-6 py-3">
                    <span className="inline-flex items-center gap-1 text-gray-300">
                      <BarChart2 size={12} className="text-gray-500" />
                      {user.portfolio_count}
                    </span>
                  </td>
                  <td className="px-6 py-3 text-gray-500 text-xs">
                    {new Date(user.created_at).toLocaleDateString("id-ID", {
                      day: "2-digit", month: "short", year: "numeric",
                    })}
                  </td>
                  <td className="px-6 py-3">
                    <button
                      onClick={() => toggleRole(user)}
                      disabled={updatingId === user.id}
                      className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium transition disabled:opacity-50 ${
                        user.role === "admin"
                          ? "bg-gray-800 text-gray-400 hover:bg-red-900 hover:text-red-300"
                          : "bg-gray-800 text-gray-400 hover:bg-indigo-900 hover:text-indigo-300"
                      }`}
                    >
                      <UserCheck size={12} />
                      {updatingId === user.id ? "…" : user.role === "admin" ? "Demote" : "Promote"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* Footer */}
        {!loading && filtered.length > 0 && (
          <div className="px-6 py-3 border-t border-gray-800 text-xs text-gray-600">
            Showing {filtered.length} of {users.length} accounts
          </div>
        )}
      </div>
    </div>
  );
}
