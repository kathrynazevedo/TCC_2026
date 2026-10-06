import React, { createContext, useContext } from 'react';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  // Simulamos que você está logado permanentemente no sistema local
  const value = {
    isAuthenticated: true,
    user: { 
      name: "Renan Albuquerque", 
      role: "Administrador do Sistema" 
    },
    login: () => {},
    logout: () => {},
    isLoading: false
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);