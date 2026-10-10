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
      <div role="alert" className="mx-auto mt-16 max-w-xl border border-destructive/40 border-t-4 border-t-destructive bg-card p-6 text-center">
        <h2 className="display text-2xl text-destructive">Algo deu errado nesta tela</h2>
        <p className="mt-2 font-mono text-sm text-muted-foreground">{this.state.error.message}</p>
        <button
          onClick={() => window.location.reload()}
          className="mt-5 bg-destructive px-5 py-2.5 font-mono text-xs font-semibold uppercase tracking-wider text-destructive-foreground hover:bg-destructive/90"
        >
          Recarregar
        </button>
      </div>
    );
  }
}
