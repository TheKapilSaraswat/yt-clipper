import { Link } from "react-router-dom";

export default function Privacy() {
  return (
    <div className="min-h-screen bg-[#0f0f0f] text-white px-6 py-12">
      <div className="max-w-3xl mx-auto">
        <Link to="/" className="text-[#ff0044] hover:underline mb-8 inline-block">&larr; Back</Link>
        <h1 className="text-3xl font-bold mb-6">Privacy Policy</h1>
        <div className="text-gray-400 space-y-4 leading-relaxed">
          <p>We collect your name and email when you join the waitlist. This information is used solely to notify you about product updates and beta access.</p>
          <p>We use Google Analytics and Microsoft Clarity to understand how visitors use our site. These services may collect anonymized usage data.</p>
          <p>We do not sell, share, or rent your personal information to third parties.</p>
          <p>You can request deletion of your data at any time by contacting us.</p>
          <p className="text-gray-500 text-sm mt-8">Last updated: June 2026</p>
        </div>
      </div>
    </div>
  );
}
