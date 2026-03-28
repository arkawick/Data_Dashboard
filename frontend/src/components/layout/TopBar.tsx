import { useNavigate } from "react-router-dom";
import { LogOut, User } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/Button";

interface TopBarProps {
  sidebarCollapsed: boolean;
}

export function TopBar({ sidebarCollapsed }: TopBarProps) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <header
      className="fixed top-0 right-0 h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6 z-20 transition-all duration-300"
      style={{ left: sidebarCollapsed ? 64 : 240 }}
    >
      <h1 className="text-base font-semibold text-gray-900">GraphRAG Dashboard</h1>

      <div className="flex items-center gap-3">
        {user && (
          <div className="flex items-center gap-2 text-sm text-gray-600 bg-gray-50 rounded-lg px-3 py-1.5 border border-gray-200">
            <User className="h-3.5 w-3.5 text-gray-400" />
            <span className="font-medium">{user.username}</span>
            <span className="text-gray-400">·</span>
            <span className="text-gray-400 capitalize">{user.role}</span>
          </div>
        )}
        <Button variant="ghost" size="sm" onClick={handleLogout} className="gap-1.5">
          <LogOut className="h-4 w-4" />
          Logout
        </Button>
      </div>
    </header>
  );
}
