import React, { createContext, useContext } from 'react';

// Autenticação simulada: o TCC não tem login. O usuário abaixo é exibido na barra lateral e no topo.
const value = {
  isAuthenticated: true,
  user: {
    name: "Renan Albuquerque",
    role: "Administrador do Sistema",
  },
};

const AuthContext = createContext(value);

export const AuthProvider = ({ children }) => (
  <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
);

export const useAuth = () => useContext(AuthContext);
