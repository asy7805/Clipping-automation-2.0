import { Link, useLocation, Outlet } from "react-router-dom";
import { 
  LayoutDashboard, 
  Film, 
  BarChart3, 
  Settings, 
  ChevronRight
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { MobileBottomNav } from "@/components/MobileBottomNav";
import { useIsMobile } from "@/hooks/use-mobile";

const navItems = [
  { icon: LayoutDashboard, label: "Dashboard", path: "/dashboard" },
  { icon: Film, label: "Clips Library", path: "/dashboard/clips" },
  { icon: BarChart3, label: "Analytics", path: "/dashboard/analytics" },
  { icon: Settings, label: "Settings", path: "/dashboard/settings" },
];

export const DashboardLayout = () => {
  const location = useLocation();
  const isMobile = useIsMobile();

  return (
    <div className="min-h-screen bg-background flex relative">
      {/* Animated background mesh */}
      <div className="fixed inset-0 mesh-gradient opacity-50 pointer-events-none" />
      
      {/* Sidebar - Hidden on mobile */}
      <aside className="hidden md:flex w-64 glass-strong flex-col relative z-10 border-r border-white/10">
        {/* Logo */}
        <div className="p-6 border-b border-white/10">
          <Link to="/" className="flex items-center gap-3 group">
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-br from-primary to-pink-500 rounded-xl blur-md opacity-50 group-hover:opacity-75 transition-opacity" />
              <div className="relative w-12 h-12 rounded-xl bg-gradient-to-br from-primary via-purple-500 to-pink-500 flex items-center justify-center shadow-lg shadow-primary/50 group-hover:shadow-primary/70 transition-all">
                <Film className="w-7 h-7 text-white" />
              </div>
            </div>
            <div>
              <h1 className="font-bold text-lg text-foreground group-hover:text-primary transition-colors">
                Clipping Auto
              </h1>
              <p className="text-xs font-semibold bg-gradient-to-r from-primary to-pink-500 bg-clip-text text-transparent">
                AI-Powered 2.0
              </p>
            </div>
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            
            return (
              <Link key={item.path} to={item.path}>
                <Button
                  variant="ghost"
                  className={cn(
                    "w-full justify-start gap-3 transition-all duration-200",
                    isActive 
                      ? "bg-primary/10 text-primary hover:bg-primary/20 hover:text-primary border border-primary/20" 
                      : "hover:bg-white/5 text-foreground/80 hover:text-foreground"
                  )}
                >
                  <Icon className="w-5 h-5" />
                  {item.label}
                  {isActive && <ChevronRight className="w-4 h-4 ml-auto" />}
                </Button>
              </Link>
            );
          })}
        </nav>

        {/* User Profile */}
        <div className="p-4 border-t border-white/10">
          <div className="flex items-center gap-3 p-2 rounded-lg bg-muted/20">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-pink-500 flex items-center justify-center text-white font-bold">
              A
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-foreground truncate">Admin</p>
              <p className="text-xs text-muted-foreground">Local User</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col relative z-10">
        {/* Top Bar */}
        <header className="h-16 glass sticky top-0 z-40 flex items-center justify-between px-4 md:px-6 border-b border-white/10">
          <div className="flex-1">
            <h2 className="text-lg font-semibold text-foreground">
              {location.pathname === "/dashboard" && "Dashboard"}
              {location.pathname === "/dashboard/clips" && "Clips Library"}
              {location.pathname === "/dashboard/analytics" && "Analytics"}
              {location.pathname === "/dashboard/settings" && "Settings"}
            </h2>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-muted/30">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-pink-500 flex items-center justify-center text-white font-bold text-sm">
                A
              </div>
              <span className="text-sm font-medium text-foreground">Admin</span>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-auto pb-20 md:pb-0">
          <Outlet />
        </main>
      </div>

      {/* Mobile Bottom Navigation */}
      <MobileBottomNav />
    </div>
  );
};
