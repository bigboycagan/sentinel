import { Routes, Route } from "react-router-dom";
import Landing from "@/pages/Landing";
import Dashboard from "@/pages/Dashboard";
import Analyzer from "@/pages/Analyzer";
import History from "@/pages/History";
import Rules from "@/pages/Rules";
import Settings from "@/pages/Settings";
import NotFound from "@/pages/NotFound";

// One <Route> per page in src/pages; BrowserRouter already wraps this in main.tsx.
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/analyzer" element={<Analyzer />} />
      <Route path="/history" element={<History />} />
      <Route path="/rules" element={<Rules />} />
      <Route path="/settings" element={<Settings />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
