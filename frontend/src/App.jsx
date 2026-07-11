import React from "react";
import { BrowserRouter as Router, Routes, Route, Navigate, Link, useNavigate, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Chatbot from "./pages/Chatbot";
import EmotionCapture from "./pages/EmotionCapture";
import { GraduationCap, LayoutDashboard, Bot, Heart, LogOut, Menu } from "lucide-react";

const PrivateRoute = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500" />
      </div>
    );
  }

  return user ? children : <Navigate to="/login" replace />;
};

const Layout = ({ children }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const navItems = [
    { label: "Dashboard", path: "/", icon: <LayoutDashboard size={18} /> },
    { label: "AI Tutor", path: "/chatbot", icon: <Bot size={18} /> },
    { label: "Welfare Track", path: "/emotions", icon: <Heart size={18} /> },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-900/60 backdrop-blur-md border-r border-slate-800/80 p-6 flex flex-col justify-between shrink-0 hidden md:flex">
        <div className="space-y-8">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-3 px-2">
            <div className="w-9 h-9 bg-blue-500/10 border border-blue-500/25 rounded-xl flex items-center justify-center text-blue-400">
              <GraduationCap size={20} />
            </div>
            <span className="font-extrabold text-white text-lg tracking-tight">SkillBuddy</span>
          </Link>

          {/* Navigation Links */}
          <nav className="space-y-1">
            {navItems.map((item) => {
              const active = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all ${
                    active
                      ? "bg-blue-600 text-white shadow-lg shadow-blue-500/10"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/40"
                  }`}
                >
                  {item.icon}
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* User profile & Log out */}
        <div className="border-t border-slate-800/80 pt-6">
          <div className="flex items-center justify-between px-2 mb-4">
            <div className="overflow-hidden">
              <h4 className="text-sm font-bold text-white truncate">
                {user?.first_name ? `${user.first_name} ${user.last_name}` : user?.username}
              </h4>
              <p className="text-slate-500 text-xs font-semibold uppercase mt-0.5 tracking-wide truncate">
                {user?.role_label || "Student"}
              </p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 bg-slate-950 border border-slate-800/80 hover:bg-red-500/10 hover:text-red-400 text-slate-400 text-sm font-semibold py-2.5 rounded-xl transition-all"
          >
            <LogOut size={16} />
            Log Out
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile Header */}
        <header className="bg-slate-900/60 backdrop-blur-md border-b border-slate-800/80 h-16 px-6 flex items-center justify-between md:hidden shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-500/10 border border-blue-500/25 rounded-lg flex items-center justify-center text-blue-400">
              <GraduationCap size={16} />
            </div>
            <span className="font-extrabold text-white text-md tracking-tight">SkillBuddy</span>
          </div>

          <button onClick={handleLogout} className="text-slate-400 hover:text-red-400 p-2">
            <LogOut size={18} />
          </button>
        </header>

        {/* Dynamic page contents wrapper */}
        <main className="flex-1 p-6 md:p-8 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
};

const App = () => {
  return (
    <Router>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/*"
            element={
              <PrivateRoute>
                <Layout>
                  <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/chatbot" element={<Chatbot />} />
                    <Route path="/emotions" element={<EmotionCapture />} />
                  </Routes>
                </Layout>
              </PrivateRoute>
            }
          />
        </Routes>
      </AuthProvider>
    </Router>
  );
};

export default App;
