import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

export default function Landing() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: "",
    email: "",
    niche: "",
    goal: "",
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);

  const ref = searchParams.get("ref");

  useEffect(() => {
    if (ref) {
      localStorage.setItem("ref", ref);
    }
    fetch("/api/waitlist/visit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        source: document.referrer || "direct",
        ref: ref || undefined,
      }),
    }).catch(() => {});
  }, []);

  function handleChange(e) {
    setForm({ ...form, [e.target.name]: e.target.value });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setMessage(null);

    try {
      const storedRef = localStorage.getItem("ref");
      const res = await fetch("/api/waitlist/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...form, referredBy: ref || storedRef }),
      });
      const data = await res.json();

      if (!res.ok) {
        setError(data.error);
        return;
      }

      navigate(`/thank-you?position=${data.position}&code=${data.referralCode}`);
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#0f0f0f] text-white">
      {/* Nav */}
      <nav className="flex items-center justify-between px-6 py-4 max-w-6xl mx-auto">
        <span className="text-2xl font-bold text-[#ff0044]">YT Clipper</span>
        <a
          href="#waitlist"
          className="bg-[#ff0044] px-5 py-2 rounded-full text-sm font-semibold hover:bg-[#cc0033] transition"
        >
          Join Waitlist
        </a>
      </nav>

      {/* Hero */}
      <section className="text-center px-6 pt-20 pb-16 max-w-4xl mx-auto">
        <h1 className="text-5xl md:text-6xl font-bold leading-tight">
          Automated YouTube Shorts,{" "}
          <span className="text-[#ff0044]">On Autopilot</span>
        </h1>
        <p className="text-gray-400 text-lg mt-6 max-w-2xl mx-auto">
          YT Clipper discovers trending videos, checks for copyright, clips the
          best moments, and uploads Shorts to your channel — automatically.
        </p>
        <div className="mt-8 flex flex-col sm:flex-row gap-4 justify-center">
          <a
            href="#waitlist"
            className="bg-[#ff0044] px-8 py-3 rounded-full font-semibold text-lg hover:bg-[#cc0033] transition"
          >
            Get Early Access
          </a>
          <a
            href="#features"
            className="border border-gray-600 px-8 py-3 rounded-full font-semibold text-lg hover:border-gray-400 transition"
          >
            See How It Works
          </a>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="px-6 py-20 max-w-6xl mx-auto">
        <h2 className="text-3xl font-bold text-center mb-12">
          What YT Clipper Does
        </h2>
        <div className="grid md:grid-cols-3 gap-8">
          {[
            {
              title: "Discover Trending Content",
              desc: "Scans YouTube for trending videos, checks safety, and picks the best candidates based on view count and risk level.",
            },
            {
              title: "Clip & Convert to Shorts",
              desc: "Downloads the first 30 seconds, converts to vertical 9:16 format, and optimizes it for the Shorts feed.",
            },
            {
              title: "Auto-Upload Daily",
              desc: "Uploads 6 fresh Shorts to your YouTube channel every day with SEO-optimized captions and tags.",
            },
          ].map((f) => (
            <div key={f.title} className="bg-[#1a1a1a] rounded-xl p-6 border border-gray-800">
              <h3 className="text-xl font-semibold mb-3">{f.title}</h3>
              <p className="text-gray-400 leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Demo */}
      <section className="px-6 py-20 max-w-4xl mx-auto text-center">
        <h2 className="text-3xl font-bold mb-8">See It In Action</h2>
        <div className="bg-[#1a1a1a] rounded-xl border border-gray-800 aspect-video flex items-center justify-center text-gray-500">
          <div className="text-center">
            <span className="text-6xl">▶</span>
            <p className="mt-4">Demo video coming soon</p>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="px-6 py-20 max-w-3xl mx-auto">
        <h2 className="text-3xl font-bold text-center mb-12">
          Frequently Asked Questions
        </h2>
        {[
          {
            q: "How does YT Clipper avoid copyright issues?",
            a: "Every video goes through a multi-step safety check: title keywords, description patterns, channel verification, follower count, music categories, and engagement metrics. HIGH risk videos are automatically skipped.",
          },
          {
            q: "How many Shorts can I post per day?",
            a: "The pipeline uploads up to 6 Shorts per day by default, which is the YouTube API limit. You can adjust this in the config.",
          },
          {
            q: "Do I need technical skills to use it?",
            a: "Basic command-line familiarity helps, but the GUI makes it easy. Set up once, and the daily pipeline runs automatically.",
          },
          {
            q: "What do I need to get started?",
            a: "Python, yt-dlp, ffmpeg, and a Google OAuth client_secret.json file. The setup script handles dependencies.",
          },
        ].map((faq) => (
          <details key={faq.q} className="bg-[#1a1a1a] rounded-xl p-5 mb-4 border border-gray-800 group">
            <summary className="font-semibold cursor-pointer list-none flex justify-between items-center">
              {faq.q}
              <span className="text-gray-500 group-open:rotate-180 transition">▼</span>
            </summary>
            <p className="mt-4 text-gray-400 leading-relaxed">{faq.a}</p>
          </details>
        ))}
      </section>

      {/* Waitlist Form */}
      <section id="waitlist" className="px-6 py-20 max-w-lg mx-auto">
        <h2 className="text-3xl font-bold text-center mb-4">Join the Waitlist</h2>
        <p className="text-gray-400 text-center mb-8">
          Be the first to get access when we launch.
        </p>

        {message && (
          <div className="bg-green-900/50 border border-green-700 text-green-300 rounded-xl p-4 mb-6 text-center">
            {message}
          </div>
        )}
        {error && (
          <div className="bg-red-900/50 border border-red-700 text-red-300 rounded-xl p-4 mb-6 text-center">
            {error}
          </div>
        )}

        <form
          onSubmit={handleSubmit}
          className="bg-[#1a1a1a] rounded-xl p-8 border border-gray-800 space-y-5"
        >
          <div>
            <label className="block text-sm text-gray-400 mb-1">Name *</label>
            <input
              name="name"
              value={form.name}
              onChange={handleChange}
              required
              className="w-full bg-[#0f0f0f] border border-gray-700 rounded-lg px-4 py-3 focus:outline-none focus:border-[#ff0044] transition"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Email *</label>
            <input
              name="email"
              type="email"
              value={form.email}
              onChange={handleChange}
              required
              className="w-full bg-[#0f0f0f] border border-gray-700 rounded-lg px-4 py-3 focus:outline-none focus:border-[#ff0044] transition"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">
              Interested Niche (optional)
            </label>
            <select
              name="niche"
              value={form.niche}
              onChange={handleChange}
              className="w-full bg-[#0f0f0f] border border-gray-700 rounded-lg px-4 py-3 focus:outline-none focus:border-[#ff0044] transition"
            >
              <option value="">Select...</option>
              <option value="gaming">Gaming</option>
              <option value="tech">Tech</option>
              <option value="entertainment">Entertainment</option>
              <option value="sports">Sports</option>
              <option value="news">News</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">
              Your Goal (optional)
            </label>
            <select
              name="goal"
              value={form.goal}
              onChange={handleChange}
              className="w-full bg-[#0f0f0f] border border-gray-700 rounded-lg px-4 py-3 focus:outline-none focus:border-[#ff0044] transition"
            >
              <option value="">Select...</option>
              <option value="first-channel">Grow my first channel</option>
              <option value="passive-income">Make passive income</option>
              <option value="existing-channel">Already have a channel</option>
              <option value="curious">Just curious</option>
            </select>
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#ff0044] py-3 rounded-lg font-semibold text-lg hover:bg-[#cc0033] transition disabled:opacity-50"
          >
            {loading ? "Joining..." : "Join the Waitlist"}
          </button>
        </form>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-800 px-6 py-8 text-center text-sm text-gray-500">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row justify-between items-center gap-4">
          <span className="text-[#ff0044] font-bold">YT Clipper</span>
          <div className="flex gap-6">
            <a href="/privacy" className="hover:text-gray-300 transition">Privacy</a>
            <a href="/terms" className="hover:text-gray-300 transition">Terms</a>
          </div>
          <span>&copy; 2026 YT Clipper. All rights reserved.</span>
        </div>
      </footer>
    </div>
  );
}
