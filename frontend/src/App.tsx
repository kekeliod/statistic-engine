import { Link, Outlet } from "react-router-dom";

export default function App() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <Link to="/" className="font-semibold text-slate-900">
            Research Data Analysis Agent
          </Link>
          <nav className="text-sm">
            <Link to="/" className="text-slate-600 hover:text-slate-900">
              Projects
            </Link>
          </nav>
        </div>
      </header>
      <Outlet />
    </div>
  );
}
