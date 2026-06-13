import { useState, useEffect } from "react";

function authFetch(url, opts = {}) {
  const token = sessionStorage.getItem("adminToken");
  return fetch(url, {
    ...opts,
    headers: {
      ...opts.headers,
      Authorization: `Bearer ${token}`,
    },
  });
}

export default function Admin() {
  const [authenticated, setAuthenticated] = useState(!!sessionStorage.getItem("adminToken"));
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [searchResults, setSearchResults] = useState(null);

  useEffect(() => {
    if (!authenticated) {
      setLoading(false);
      return;
    }
    authFetch("/api/analytics/dashboard")
      .then((r) => {
        if (r.status === 401) {
          sessionStorage.removeItem("adminToken");
          setAuthenticated(false);
          return null;
        }
        return r.json();
      })
      .then((d) => {
        if (d) setData(d);
      })
      .finally(() => setLoading(false));
  }, [authenticated]);

  async function handleLogin(e) {
    e.preventDefault();
    setLoginError(null);
    const res = await fetch("/api/analytics/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
    const result = await res.json();
    if (!res.ok) {
      setLoginError(result.error);
      return;
    }
    sessionStorage.setItem("adminToken", result.token);
    setAuthenticated(true);
  }

  async function handleSearch(q) {
    setSearch(q);
    if (!q.trim()) {
      setSearchResults(null);
      return;
    }
    const res = await authFetch(`/api/analytics/search?q=${encodeURIComponent(q)}`);
    if (res.status === 401) {
      sessionStorage.removeItem("adminToken");
      setAuthenticated(false);
      return;
    }
    const users = await res.json();
    setSearchResults(users);
  }

  async function deleteUser(id) {
    if (!confirm("Delete this entry?")) return;
    const res = await authFetch(`/api/analytics/user/${id}`, { method: "DELETE" });
    if (res.status === 401) {
      sessionStorage.removeItem("adminToken");
      setAuthenticated(false);
      return;
    }
    setSearchResults(searchResults.filter((u) => u._id !== id));
    setData(null);
    authFetch("/api/analytics/dashboard")
      .then((r) => r.json())
      .then(setData);
  }

  async function exportCSV() {
    const token = sessionStorage.getItem("adminToken");
    window.open(`/api/analytics/export?token=${token}`, "_blank");
  }

  if (!authenticated) {
    return (
      <div className="min-h-screen bg-[#0f0f0f] text-white flex items-center justify-center">
        <form onSubmit={handleLogin} className="bg-[#1a1a1a] rounded-xl p-8 border border-gray-800 w-full max-w-sm space-y-5">
          <h1 className="text-2xl font-bold text-center">Admin Login</h1>
          {loginError && (
            <div className="bg-red-900/50 border border-red-700 text-red-300 rounded-lg p-3 text-center text-sm">
              {loginError}
            </div>
          )}
          <div>
            <label className="block text-sm text-gray-400 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoFocus
              className="w-full bg-[#0f0f0f] border border-gray-700 rounded-lg px-4 py-3 focus:outline-none focus:border-[#ff0044] transition"
            />
          </div>
          <button
            type="submit"
            className="w-full bg-[#ff0044] py-3 rounded-lg font-semibold hover:bg-[#cc0033] transition"
          >
            Login
          </button>
        </form>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0f0f0f] text-white flex items-center justify-center">
        Loading...
      </div>
    );
  }

  const users = searchResults || data?.users || [];

  return (
    <div className="min-h-screen bg-[#0f0f0f] text-white">
      <div className="max-w-6xl mx-auto px-6 py-8">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold">Admin Dashboard</h1>
          <div className="flex gap-3">
            <button
              onClick={exportCSV}
              className="bg-[#ff0044] px-5 py-2 rounded-lg text-sm font-semibold hover:bg-[#cc0033] transition"
            >
              Export CSV
            </button>
            <button
              onClick={() => { sessionStorage.removeItem("adminToken"); setAuthenticated(false); }}
              className="border border-gray-600 px-5 py-2 rounded-lg text-sm font-semibold hover:border-gray-400 transition"
            >
              Logout
            </button>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[
            { label: "Total Signups", value: data?.total || 0 },
            { label: "Today's Signups", value: data?.todaySignups || 0 },
            { label: "Referral Signups", value: data?.referralSignups || 0 },
            { label: "Conversion Rate", value: `${data?.conversionRate || 0}%` },
            { label: "Total Visits", value: data?.totalVisits || 0 },
            { label: "Unique Visitors", value: data?.uniqueVisitors || 0 },
            { label: "Link Clicks", value: data?.linkClicks || 0 },
            { label: "Signed Up from Visit", value: data?.signedUpVisitors || 0 },
          ].map((m) => (
            <div key={m.label} className="bg-[#1a1a1a] rounded-xl p-5 border border-gray-800">
              <p className="text-gray-400 text-sm">{m.label}</p>
              <p className="text-3xl font-bold mt-1">{m.value}</p>
            </div>
          ))}
        </div>

        <div className="mb-6">
          <input
            placeholder="Search by name or email..."
            value={search}
            onChange={(e) => handleSearch(e.target.value)}
            className="w-full max-w-md bg-[#1a1a1a] border border-gray-700 rounded-lg px-4 py-3 focus:outline-none focus:border-[#ff0044] transition"
          />
        </div>

        <div className="bg-[#1a1a1a] rounded-xl border border-gray-800 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-gray-400 text-left">
                <th className="p-4">Name</th>
                <th className="p-4">Email</th>
                <th className="p-4">Niche</th>
                <th className="p-4">Goal</th>
                <th className="p-4">Position</th>
                <th className="p-4">Referrals</th>
                <th className="p-4">Date</th>
                <th className="p-4"></th>
              </tr>
            </thead>
            <tbody>
              {users.length === 0 ? (
                <tr>
                  <td colSpan={8} className="p-8 text-center text-gray-500">
                    No signups yet.
                  </td>
                </tr>
              ) : (
                users.map((u) => (
                  <tr key={u._id} className="border-b border-gray-800/50 hover:bg-[#0f0f0f] transition">
                    <td className="p-4">{u.name}</td>
                    <td className="p-4 text-gray-400">{u.email}</td>
                    <td className="p-4 text-gray-400">{u.niche || "—"}</td>
                    <td className="p-4 text-gray-400">{u.goal || "—"}</td>
                    <td className="p-4">#{u.position}</td>
                    <td className="p-4">{u.referralCount}</td>
                    <td className="p-4 text-gray-400">
                      {new Date(u.createdAt).toLocaleDateString()}
                    </td>
                    <td className="p-4">
                      <button
                        onClick={() => deleteUser(u._id)}
                        className="text-red-400 hover:text-red-300 transition text-xs"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="mt-8">
          <h2 className="text-xl font-bold mb-4">Recent Page Visits</h2>
          <div className="bg-[#1a1a1a] rounded-xl border border-gray-800 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-gray-400 text-left">
                  <th className="p-4">Source</th>
                  <th className="p-4">Ref Code</th>
                  <th className="p-4">IP</th>
                  <th className="p-4">Signed Up</th>
                  <th className="p-4">Date</th>
                </tr>
              </thead>
              <tbody>
                {(data?.recentVisits || []).length === 0 ? (
                  <tr>
                    <td colSpan={5} className="p-8 text-center text-gray-500">
                      No visits yet.
                    </td>
                  </tr>
                ) : (
                  data?.recentVisits?.map((v) => (
                    <tr key={v._id} className="border-b border-gray-800/50 hover:bg-[#0f0f0f] transition">
                      <td className="p-4 text-gray-400">{v.source || "direct"}</td>
                      <td className="p-4 text-gray-400">{v.referralCode || "—"}</td>
                      <td className="p-4 text-gray-400">{v.ip}</td>
                      <td className="p-4">
                        {v.signedUp ? (
                          <span className="text-green-400">Yes</span>
                        ) : (
                          <span className="text-gray-500">No</span>
                        )}
                      </td>
                      <td className="p-4 text-gray-400">
                        {new Date(v.createdAt).toLocaleString()}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}