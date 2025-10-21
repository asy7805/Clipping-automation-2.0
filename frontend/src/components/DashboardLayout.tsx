import { Link, useLocation, Outlet } from "react-router-dom";
import { 
  LayoutDashboard, 
  Film, 
  BarChart3, 
  Settings, 
  Activity, 
  Search, 
  Bell,
  ChevronRight
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { MobileBottomNav } from "@/components/MobileBottomNav";
import { useIsMobile } from "@/hooks/use-mobile";

const navItems = [
  { icon: LayoutDashboard, label: "Dashboard", path: "/dashboard" },
  { icon: Film, label: "Clips Library", path: "/clips" },
  { icon: BarChart3, label: "Analytics", path: "/analytics" },
  { icon: Settings, label: "Settings", path: "/settings" },
];

const quickChannels = [
  { name: "nater4l", live: true },
  { name: "jordanbentley", live: true },
  { name: "asspizza730", live: false },
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

        {/* Quick Channels */}
        <div className="p-4 border-t border-white/10">
          <p className="text-xs font-semibold text-muted-foreground mb-3 uppercase tracking-wider">Quick Access</p>
          <div className="space-y-2">
            {quickChannels.map((channel) => (
              <div key={channel.name} className="flex items-center gap-2 text-sm px-2 py-1.5 rounded-md hover:bg-white/5 transition-colors cursor-pointer">
                <span className={cn(
                  "w-2 h-2 rounded-full",
                  channel.live ? "bg-success pulse-dot" : "bg-muted"
                )} />
                <span className="text-foreground/90">{channel.name}</span>
              </div>
            ))}
            <Button variant="ghost" size="sm" className="w-full justify-start text-primary hover:text-primary hover:bg-primary/10 mt-2">
              <span className="text-xl mr-2">+</span> Add Channel
            </Button>
          </div>
        </div>

        {/* User Profile */}
        <div className="p-4 border-t border-white/10">
          <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-white/5 transition-colors cursor-pointer">
            <Avatar className="border-2 border-primary/50">
              <AvatarImage src="https://api.dicebear.com/7.x/avataaars/svg?seed=user" />
              <AvatarFallback>U</AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-foreground truncate">Admin User</p>
              <p className="text-xs text-primary">Pro Plan</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col relative z-10">
        {/* Top Bar */}
        <header className="h-16 glass sticky top-0 z-40 flex items-center justify-between px-4 md:px-6 border-b border-white/10">
          <div className="flex-1 max-w-xl">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input 
                type="text"
                placeholder="Search clips, channels..."
                className="w-full pl-10 pr-4 py-2 bg-background/50 border border-white/10 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent placeholder:text-muted-foreground transition-all"
              />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" className="relative hover:bg-white/5">
              <Bell className="w-5 h-5" />
              <Badge className="absolute -top-1 -right-1 w-5 h-5 flex items-center justify-center p-0 bg-destructive text-xs border-2 border-background">
                3
              </Badge>
            </Button>
            <Avatar className="cursor-pointer ring-2 ring-primary/50 hover:ring-primary transition-all">
              <AvatarImage src="https://api.dicebear.com/7.x/avataaars/svg?seed=user" />
              <AvatarFallback>U</AvatarFallback>
            </Avatar>
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
