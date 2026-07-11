import React, { createContext, useState, useEffect, useContext } from "react";
import api from "../services/api";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [student, setStudent] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem("access_token");
      const storedUser = localStorage.getItem("user_info");
      const storedStudent = localStorage.getItem("student_info");

      if (token && storedUser) {
        setUser(JSON.parse(storedUser));
        if (storedStudent) {
          setStudent(JSON.parse(storedStudent));
        }
      }
      setLoading(false);
    };
    checkAuth();
  }, []);

  const login = async (username, password) => {
    try {
      const response = await api.post("/api/auth/login/", {
        username,
        password,
      });

      const { access, refresh, user: userData, student: studentData } = response.data;
      localStorage.setItem("access_token", access);
      localStorage.setItem("refresh_token", refresh);
      localStorage.setItem("user_info", JSON.stringify(userData));
      
      setUser(userData);
      if (studentData) {
        localStorage.setItem("student_info", JSON.stringify(studentData));
        setStudent(studentData);
      } else {
        localStorage.removeItem("student_info");
        setStudent(null);
      }
      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || "Authentication failed",
      };
    }
  };

  const logout = () => {
    localStorage.clear();
    setUser(null);
    setStudent(null);
  };

  return (
    <AuthContext.Provider value={{ user, student, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
