import { Component, type ReactNode } from "react";
import { ErrorState } from "./States";

export class ErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null };
  static getDerivedStateFromError(error: Error) {
    return { error };
  }
  render() {
    if (this.state.error) {
      return <ErrorState error={this.state.error} onRetry={() => this.setState({ error: null })} className="mt-10" />;
    }
    return this.props.children;
  }
}
