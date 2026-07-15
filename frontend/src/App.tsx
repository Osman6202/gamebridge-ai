import { Routes, Route, Navigate } from "react-router-dom";
import { getToken } from "./api";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import TestRunner from "./pages/TestRunner";

function RequireAuth({ children }: { children: JSX.Element }) {
  return getToken() ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<RequireAuth><Dashboard /></RequireAuth>} />
      <Route path="/projects/:id/tests" element={<RequireAuth><TestRunner /></RequireAuth>} />
    </Routes>
  );
}
