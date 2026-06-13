import { Routes, Route } from "react-router-dom";
import Landing from "./pages/Landing";
import ThankYou from "./pages/ThankYou";
import Admin from "./pages/Admin";
import Privacy from "./pages/Privacy";
import Terms from "./pages/Terms";
import ReferralRedirect from "./pages/ReferralRedirect";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/thank-you" element={<ThankYou />} />
      <Route path="/admin" element={<Admin />} />
      <Route path="/privacy" element={<Privacy />} />
      <Route path="/terms" element={<Terms />} />
      <Route path="/ref/:code" element={<ReferralRedirect />} />
    </Routes>
  );
}
