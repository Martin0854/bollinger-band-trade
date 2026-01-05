import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { api } from '../services/api';
import type { User } from '../types';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (token: string, fingerprint: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

const TOKEN_KEY = 'trading_wizard_token';
const FINGERPRINT_KEY = 'trading_wizard_fingerprint';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check for existing token on mount
    const token = localStorage.getItem(TOKEN_KEY);
    const fingerprint = localStorage.getItem(FINGERPRINT_KEY);

    if (token && fingerprint) {
      api.setToken(token);
      // Set minimal user info from stored fingerprint
      setUser({
        id: '',
        fingerprint,
        nickname: null,
        created_at: '',
        last_login_at: null,
      });
    }
    setIsLoading(false);
  }, []);

  const login = (token: string, fingerprint: string) => {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(FINGERPRINT_KEY, fingerprint);
    api.setToken(token);
    setUser({
      id: '',
      fingerprint,
      nickname: null,
      created_at: '',
      last_login_at: null,
    });
  };

  const logout = async () => {
    try {
      // Call logout endpoint
      await api.post('/auth/logout', {});
    } catch {
      // Ignore errors on logout
    } finally {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(FINGERPRINT_KEY);
      api.setToken(null);
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
