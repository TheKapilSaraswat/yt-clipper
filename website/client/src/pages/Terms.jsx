import { Link } from "react-router-dom";

export default function Terms() {
  return (
    <div className="min-h-screen bg-[#0f0f0f] text-white px-6 py-12">
      <div className="max-w-3xl mx-auto">
        <Link to="/" className="text-[#ff0044] hover:underline mb-8 inline-block">&larr; Back</Link>
        <h1 className="text-3xl font-bold mb-6">Terms & Conditions</h1>
        <div className="text-gray-400 space-y-4 leading-relaxed">
          <p>YT Clipper is provided as-is. By using the waitlist and service, you agree to these terms.</p>
          <p>You are responsible for complying with YouTube's Terms of Service when using our tool to upload content.</p>
          <p>We reserve the right to modify or discontinue the service at any time without notice.</p>
          <p>We are not responsible for any copyright claims or policy violations resulting from your use of the tool.</p>
          <p className="text-gray-500 text-sm mt-8">Last updated: June 2026</p>
        </div>
      </div>
    </div>
  );
}
