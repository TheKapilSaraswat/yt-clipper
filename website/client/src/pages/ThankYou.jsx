import { useSearchParams, Link } from "react-router-dom";

export default function ThankYou() {
  const [searchParams] = useSearchParams();
  const position = searchParams.get("position") || "—";
  const code = searchParams.get("code") || "";

  const referralLink = code ? `${window.location.origin}/ref/${code}` : "";

  async function copyLink() {
    if (!referralLink) return;
    try {
      await navigator.clipboard.writeText(referralLink);
      alert("Referral link copied!");
    } catch {
      console.log("Copy failed");
    }
  }

  return (
    <div className="min-h-screen bg-[#0f0f0f] text-white flex items-center justify-center px-6">
      <div className="max-w-lg w-full text-center">
        <div className="text-6xl mb-6">🎉</div>
        <h1 className="text-4xl font-bold mb-4">You're on the waitlist!</h1>
        <p className="text-gray-400 text-lg mb-2">
          You're <span className="text-[#ff0044] font-bold">#{position}</span>{" "}
          on the list.
        </p>
        <p className="text-gray-500 mb-8">
          We'll keep you posted on our progress.
        </p>

        {referralLink && (
          <div className="bg-[#1a1a1a] rounded-xl p-6 border border-gray-800 mb-8">
            <p className="text-sm text-gray-400 mb-3">Share your referral link:</p>
            <div className="flex items-center gap-2">
              <input
                readOnly
                value={referralLink}
                className="flex-1 bg-[#0f0f0f] border border-gray-700 rounded-lg px-4 py-2 text-sm text-gray-300"
              />
              <button
                onClick={copyLink}
                className="bg-[#ff0044] px-4 py-2 rounded-lg text-sm font-semibold hover:bg-[#cc0033] transition whitespace-nowrap"
              >
                Copy
              </button>
            </div>
            <div className="flex gap-3 mt-4 justify-center">
              <a
                href={`https://twitter.com/intent/tweet?text=${encodeURIComponent(`I just joined the YT Clipper waitlist! Get your spot: ${referralLink}`)}`}
                target="_blank"
                rel="noopener noreferrer"
                className="bg-[#1da1f2] px-4 py-2 rounded-lg text-sm font-semibold hover:opacity-90 transition"
              >
                Share on X
              </a>
              <a
                href={`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(referralLink)}`}
                target="_blank"
                rel="noopener noreferrer"
                className="bg-[#0a66c2] px-4 py-2 rounded-lg text-sm font-semibold hover:opacity-90 transition"
              >
                Share on LinkedIn
              </a>
            </div>
          </div>
        )}

        <Link
          to="/"
          className="inline-block border border-gray-600 px-6 py-3 rounded-full hover:border-gray-400 transition"
        >
          Back to Home
        </Link>
      </div>
    </div>
  );
}
