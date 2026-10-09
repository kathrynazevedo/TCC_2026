import React from "react";

/** Evita a "tela branca": se uma página quebrar, mostra o erro e permite recarregar. */
export default class ErrorBoundary extends React.Component {
  state = { error: null };

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error("Erro de renderização:", error, info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;

    return (
      <div role="alert" className="max-w-xl mx-auto mt-16 rounded-xl border border-red-200 dark:border-red-900/50 bg-red-50 dark:bg-red-900/20 p-6 text-center">
        <h2 className="text-lg font-bold text-red-800 dark:text-red-300">Algo deu errado nesta tela</h2>
        <p className="mt-1 text-sm text-red-700 dark:text-red-300/80">{this.state.error.message}</p>
        <button
          onClick={() => window.location.reload()}
          className="mt-4 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
        >
          Recarregar
        </button>
      </div>
    );
  }
}
