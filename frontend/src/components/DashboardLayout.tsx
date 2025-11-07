import { Link, useLocation, Outlet, useNavigate } from "react-router-dom";
import { 
  LayoutDashboard, 
  Film, 
  BarChart3, 
  Settings, 
  Share2,
  ChevronRight,
  Bell,
  Scissors,
  LogOut,
  User,
  Shield
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import { MobileBottomNav } from "@/components/MobileBottomNav";
import { useIsMobile } from "@/hooks/use-mobile";
import { useState } from "react";
import NotificationCenter from "@/components/NotificationCenter";
import { useAuth } from "@/contexts/AuthContext";

const navItems = [
  { icon: LayoutDashboard, label: "Dashboard", path: "/dashboard" },
  { icon: Film, label: "Clips Library", path: "/dashboard/clips" },
  { icon: Scissors, label: "Video Editor", path: "/dashboard/editor/projects" },
  { icon: BarChart3, label: "Analytics", path: "/dashboard/analytics" },
  { icon: Share2, label: "Social Accounts", path: "/dashboard/social" },
  { icon: Settings, label: "Settings", path: "/dashboard/settings" },
];

export const DashboardLayout = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const isMobile = useIsMobile();
  const [showNotifications, setShowNotifications] = useState(false);
  const { user, signOut, isAdmin } = useAuth();

  const handleLogout = async () => {
    await signOut();
    navigate("/login");
  };

  // Get user initial for avatar
  const userInitial = user?.email?.charAt(0).toUpperCase() || "U";

  return (
    <div className="min-h-screen bg-background flex relative">
      {/* Animated background mesh */}
      <div className="fixed inset-0 mesh-gradient opacity-50 pointer-events-none" />
      
      {/* Sidebar - Fixed position, hidden on mobile */}
      <aside className="hidden md:flex w-48 glass-strong flex-col fixed left-0 top-0 z-10 border-r border-white/10 h-screen overflow-hidden">
        {/* Logo */}
        <div className="p-4 border-b border-white/10 flex-shrink-0">
          <Link to="/" className="flex items-center gap-3 group">
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-br from-primary to-pink-500 rounded-lg blur-md opacity-50 group-hover:opacity-75 transition-opacity" />
              <div className="relative w-10 h-10 rounded-lg bg-gradient-to-br from-primary via-purple-500 to-pink-500 flex items-center justify-center shadow-lg shadow-primary/50 group-hover:shadow-primary/70 transition-all">
                <Film className="w-6 h-6 text-white" />
              </div>
            </div>
            <div className="min-w-0">
              <h1 className="font-bold text-sm text-foreground group-hover:text-primary transition-colors truncate">
                Clipping Auto
              </h1>
              <p className="text-xs font-semibold bg-gradient-to-r from-primary to-pink-500 bg-clip-text text-transparent">
                AI-Powered 2.0
              </p>
            </div>
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-3 space-y-2 overflow-hidden min-h-0">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            
            return (
              <Link key={item.path} to={item.path}>
                <Button
                  variant="ghost"
                  className={cn(
                    "w-full justify-start gap-2 transition-all duration-200 text-sm h-10",
                    isActive 
                      ? "bg-primary/10 text-primary hover:bg-primary/20 hover:text-primary border border-primary/20" 
                      : "hover:bg-white/5 text-foreground/80 hover:text-foreground"
                  )}
                >
                  <Icon className="w-4 h-4" />
                  {item.label}
                  {isActive && <ChevronRight className="w-4 h-4 ml-auto" />}
                </Button>
              </Link>
            );
          })}
          
          {/* Admin button - only visible to admins */}
          {isAdmin && (
            <>
              <div className="border-t border-white/10 my-2" />
              <Link to="/dashboard/admin">
                <Button
                  variant="ghost"
                  className={cn(
                    "w-full justify-start gap-2 transition-all duration-200 text-sm h-10",
                    location.pathname === "/dashboard/admin"
                      ? "bg-yellow-500/10 text-yellow-500 hover:bg-yellow-500/20 hover:text-yellow-500 border border-yellow-500/20" 
                      : "hover:bg-white/5 text-yellow-400/80 hover:text-yellow-400"
                  )}
                >
                  <Shield className="w-4 h-4" />
                  Admin
                  {location.pathname === "/dashboard/admin" && <ChevronRight className="w-4 h-4 ml-auto" />}
                </Button>
              </Link>
            </>
          )}
        </nav>

        {/* User Profile */}
        <div className="p-4 border-t border-white/10 flex-shrink-0">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="w-full flex items-center gap-3 p-3 rounded-lg bg-muted/20 hover:bg-muted/30 transition-colors cursor-pointer">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-pink-500 flex items-center justify-center text-white font-bold text-sm">
                  {userInitial}
                </div>
                <div className="flex-1 min-w-0 text-left">
                  <p className="text-sm font-semibold text-foreground truncate">{user?.email?.split('@')[0] || 'User'}</p>
                  <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
                </div>
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>My Account</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => navigate("/dashboard/settings")}>
                <Settings className="w-4 h-4 mr-2" />
                Settings
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleLogout} className="text-destructive focus:text-destructive">
                <LogOut className="w-4 h-4 mr-2" />
                Log out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </aside>

        {/* Main Content */}
        <div className="flex-1 flex flex-col relative z-10 md:ml-48">
        {/* Top Bar */}
        <header className="h-16 glass sticky top-0 z-40 flex items-center justify-between px-4 md:px-6 border-b border-white/10">
          <div className="flex-1">
            <h2 className="text-lg font-semibold text-foreground">
              {location.pathname === "/dashboard" && "Dashboard"}
              {location.pathname === "/dashboard/clips" && "Clips Library"}
              {location.pathname === "/dashboard/analytics" && "Analytics"}
              {location.pathname === "/dashboard/social" && "Social Accounts"}
              {location.pathname === "/dashboard/settings" && "Settings"}
            </h2>
          </div>

          <div className="flex items-center gap-3">
            {/* Notification Bell */}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowNotifications(true)}
              className="relative"
            >
              <Bell className="w-5 h-5" />
              {/* Notification badge - you can add logic to show unread count */}
            </Button>
            
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="flex items-center gap-2 px-3 py-2 rounded-lg bg-muted/30 hover:bg-muted/40 transition-colors cursor-pointer">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-pink-500 flex items-center justify-center text-white font-bold text-sm">
                    {userInitial}
                  </div>
                  <span className="text-sm font-medium text-foreground hidden md:inline">{user?.email?.split('@')[0] || 'User'}</span>
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel>
                  <div className="flex flex-col space-y-1">
                    <p className="text-sm font-medium leading-none">{user?.email?.split('@')[0] || 'User'}</p>
                    <p className="text-xs leading-none text-muted-foreground">{user?.email}</p>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => navigate("/dashboard/settings")}>
                  <Settings className="w-4 h-4 mr-2" />
                  Settings
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleLogout} className="text-destructive focus:text-destructive">
                  <LogOut className="w-4 h-4 mr-2" />
                  Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-auto pb-20 md:pb-0">
          <Outlet />
        </main>
      </div>

      {/* Mobile Bottom Navigation */}
      <MobileBottomNav />
      
      {/* Notification Center */}
      <NotificationCenter 
        isOpen={showNotifications} 
        onClose={() => setShowNotifications(false)} 
      />
    </div>
  );
};
