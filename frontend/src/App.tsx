import { Route, Routes } from "react-router-dom";

import { AppLayout } from "@/components/layout/AppLayout";
import { Dashboard } from "@/pages/Dashboard";
import { TargetDetail } from "@/pages/TargetDetail";
import { Targets } from "@/pages/Targets";

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Dashboard />} />
        <Route path="targets" element={<Targets />} />
        <Route path="targets/:uuid" element={<TargetDetail />} />
      </Route>
    </Routes>
  );
}
