import React, { useState, useEffect } from "react";
import api from "../services/api";
import { Users, BookOpen, UserCheck, Calendar, Activity, BarChart3 } from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

const Dashboard = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const response = await api.get("/api/dashboard/metrics/");
        setData(response.data);
      } catch (err) {
        console.error("Failed to load dashboard metrics", err);
      } finally {
        setLoading(false);
      }
    };
    fetchMetrics();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500" />
      </div>
    );
  }

  const metrics = data?.metrics || { total_students: 0, total_faculty: 0, total_courses: 0 };
  const chartData = data?.chart_data || [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight text-white">
          Workspace Dashboard
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          Role status: <span className="text-blue-400 font-semibold">{data?.role || "Student"}</span>
        </p>
      </div>

      {/* Grid Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-6 shadow-xl flex items-center gap-5">
          <div className="w-12 h-12 bg-blue-500/10 border border-blue-500/20 rounded-xl flex items-center justify-center text-blue-400">
            <Users size={24} />
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Students</p>
            <h3 className="text-2xl font-bold text-white mt-1">{metrics.total_students}</h3>
          </div>
        </div>

        <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-6 shadow-xl flex items-center gap-5">
          <div className="w-12 h-12 bg-purple-500/10 border border-purple-500/20 rounded-xl flex items-center justify-center text-purple-400">
            <UserCheck size={24} />
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Faculty</p>
            <h3 className="text-2xl font-bold text-white mt-1">{metrics.total_faculty}</h3>
          </div>
        </div>

        <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-6 shadow-xl flex items-center gap-5">
          <div className="w-12 h-12 bg-emerald-500/10 border border-emerald-500/20 rounded-xl flex items-center justify-center text-emerald-400">
            <BookOpen size={24} />
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Courses</p>
            <h3 className="text-2xl font-bold text-white mt-1">{metrics.total_courses}</h3>
          </div>
        </div>
      </div>

      {/* Charts & Analytics */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-6 shadow-xl lg:col-span-2">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <BarChart3 size={20} className="text-blue-400" />
              LMS Analytics Summary
            </h3>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} tickLine={false} />
                <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155" }}
                  labelStyle={{ color: "#f8fafc" }}
                />
                <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} barSize={45} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-6 shadow-xl space-y-6">
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            <Activity size={20} className="text-purple-400" />
            System Status
          </h3>
          <div className="space-y-4">
            <div className="flex justify-between items-center text-sm border-b border-slate-800/80 pb-3">
              <span className="text-slate-400 flex items-center gap-2">
                <Calendar size={16} /> Semester
              </span>
              <span className="text-slate-200 font-semibold">First</span>
            </div>
            <div className="flex justify-between items-center text-sm border-b border-slate-800/80 pb-3">
              <span className="text-slate-400">Server Health</span>
              <span className="text-emerald-400 font-semibold">Healthy</span>
            </div>
            <div className="flex justify-between items-center text-sm">
              <span className="text-slate-400">Database Engine</span>
              <span className="text-slate-200 font-semibold">Active</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
