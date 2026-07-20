import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

const isDev = window.location.port === '5173';
const host = isDev ? '127.0.0.1:8000' : window.location.host;
export const API_BASE = `${window.location.protocol}//${host}/api`;

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(() => {
    return localStorage.getItem('access_token') || sessionStorage.getItem('access_token') || null;
  });

  const [refreshToken, setRefreshToken] = useState(() => {
    return localStorage.getItem('refresh_token') || sessionStorage.getItem('refresh_token') || null;
  });

  const [user, setUser] = useState(() => {
    const savedUser = localStorage.getItem('user_data') || sessionStorage.getItem('user_data');
    return savedUser ? JSON.parse(savedUser) : null;
  });

  const [loading, setLoading] = useState(true);
  const [showExpiryModal, setShowExpiryModal] = useState(false);

  // Storage selection helper based on rememberMe flag
  const saveAuthData = (accessToken, refToken, userData, rememberMe) => {
    const storage = rememberMe ? localStorage : sessionStorage;
    // Clear both first to avoid duplicates
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_data');
    sessionStorage.removeItem('access_token');
    sessionStorage.removeItem('refresh_token');
    sessionStorage.removeItem('user_data');

    storage.setItem('access_token', accessToken);
    storage.setItem('refresh_token', refToken);
    storage.setItem('user_data', JSON.stringify(userData));

    setToken(accessToken);
    setRefreshToken(refToken);
    setUser(userData);
  };

  const clearAuthData = useCallback(() => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_data');
    sessionStorage.removeItem('access_token');
    sessionStorage.removeItem('refresh_token');
    sessionStorage.removeItem('user_data');

    setToken(null);
    setRefreshToken(null);
    setUser(null);
    setShowExpiryModal(false);
  }, []);

  // Authenticated fetch wrapper
  const authFetch = useCallback(async (url, options = {}) => {
    const activeToken = token || localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
    
    const headers = {
      ...(options.headers || {}),
    };

    if (activeToken) {
      headers['Authorization'] = `Bearer ${activeToken}`;
    }

    let response = await fetch(url, { ...options, headers });

    // Handle 401 Unauthorized -> attempt token refresh
    if (response.status === 401 && refreshToken) {
      console.log("Access token expired. Attempting refresh...");
      const refreshed = await refreshAuthToken();
      if (refreshed && refreshed.access_token) {
        headers['Authorization'] = `Bearer ${refreshed.access_token}`;
        response = await fetch(url, { ...options, headers });
      } else {
        clearAuthData();
      }
    }

    return response;
  }, [token, refreshToken, clearAuthData]);

  // Login handler
  const login = async (email, password, rememberMe = false) => {
    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, remember_me: rememberMe })
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Login failed');
      }

      saveAuthData(data.access_token, data.refresh_token, data.user, rememberMe);
      return { success: true };
    } catch (err) {
      return { success: false, error: err.message };
    }
  };

  // Logout handler
  const logout = async () => {
    try {
      if (token) {
        await authFetch(`${API_BASE}/auth/logout`, { method: 'POST' });
      }
    } catch (e) {
      console.error("Logout API error:", e);
    } finally {
      clearAuthData();
    }
  };

  // Refresh token handler
  const refreshAuthToken = async () => {
    const refToken = refreshToken || localStorage.getItem('refresh_token') || sessionStorage.getItem('refresh_token');
    if (!refToken) return null;

    try {
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refToken })
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to refresh token');
      }

      const isRemembered = !!localStorage.getItem('refresh_token');
      saveAuthData(data.access_token, data.refresh_token, data.user, isRemembered);
      setShowExpiryModal(false);
      return data;
    } catch (err) {
      console.error("Token refresh failed:", err);
      clearAuthData();
      return null;
    }
  };

  // Initial session verification on mount
  useEffect(() => {
    const initAuth = async () => {
      const activeToken = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
      if (activeToken) {
        try {
          const res = await authFetch(`${API_BASE}/auth/me`);
          if (res.ok) {
            const meData = await res.json();
            setUser(meData.user);
          } else {
            clearAuthData();
          }
        } catch (e) {
          console.error("Init auth failed:", e);
        }
      }
      setLoading(false);
    };

    initAuth();
  }, [authFetch, clearAuthData]);

  // Update profile handler
  const updateProfile = async (profileData) => {
    try {
      const res = await authFetch(`${API_BASE}/auth/profile`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(profileData)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to update profile');
      setUser(data);
      const isRemembered = !!localStorage.getItem('user_data');
      const storage = isRemembered ? localStorage : sessionStorage;
      storage.setItem('user_data', JSON.stringify(data));
      return { success: true, user: data };
    } catch (err) {
      return { success: false, error: err.message };
    }
  };

  // Change password handler
  const changePassword = async (passwordData) => {
    try {
      const res = await authFetch(`${API_BASE}/auth/change-password`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(passwordData)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to change password');
      return { success: true, message: data.message };
    } catch (err) {
      return { success: false, error: err.message };
    }
  };

  const value = {
    user,
    token,
    loading,
    isAuthenticated: !!token && !!user,
    login,
    logout,
    refreshAuthToken,
    updateProfile,
    changePassword,
    authFetch,
    showExpiryModal,
    setShowExpiryModal
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
