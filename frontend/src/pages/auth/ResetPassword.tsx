import { useState, FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card } from "@/components/ui/card";
import { Film, Loader2, Check, X } from "lucide-react";
import { supabase } from "@/lib/supabase";
import { toast } from "sonner";

const ResetPassword = () => {
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  // Password strength checker
  const getPasswordStrength = (pwd: string) => {
    if (pwd.length === 0) return { strength: 0, label: "", color: "" };
    if (pwd.length < 8) return { strength: 1, label: "Weak", color: "text-red-500" };
    
    let strength = 1;
    if (pwd.length >= 8) strength++;
    if (/[A-Z]/.test(pwd)) strength++;
    if (/[0-9]/.test(pwd)) strength++;
    if (/[^A-Za-z0-9]/.test(pwd)) strength++;

    if (strength <= 2) return { strength: 2, label: "Fair", color: "text-orange-500" };
    if (strength === 3) return { strength: 3, label: "Good", color: "text-yellow-500" };
    return { strength: 4, label: "Strong", color: "text-green-500" };
  };

  const passwordStrength = getPasswordStrength(password);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");

    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    setIsLoading(true);

    try {
      const { error } = await supabase.auth.updateUser({
        password: password,
      });

      if (error) {
        toast.error(error.message);
        setError(error.message);
        setIsLoading(false);
        return;
      }

      toast.success("Password updated successfully!");
      
      // Redirect to dashboard after successful password reset
      setTimeout(() => {
        navigate("/dashboard");
      }, 1500);
    } catch (err: any) {
      toast.error(err.message || "An unexpected error occurred");
      setError(err.message || "An unexpected error occurred");
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center relative overflow-hidden">
      {/* Animated background mesh */}
      <div className="fixed inset-0 opacity-20">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/30 rounded-full blur-3xl animate-float" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-accent/30 rounded-full blur-3xl animate-float" style={{ animationDelay: '2s' }} />
      </div>

      <div className="w-full max-w-md px-6 relative z-10">
        <Card className="p-8 glass-strong border-white/10 card-hover">
          {/* Logo and header */}
          <div className="text-center mb-8">
            <div className="flex items-center justify-center gap-3 mb-4">
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-br from-primary to-pink-500 rounded-lg blur-md opacity-50" />
                <div className="relative w-12 h-12 rounded-lg bg-gradient-to-br from-primary via-purple-500 to-pink-500 flex items-center justify-center shadow-lg shadow-primary/50">
                  <Film className="w-7 h-7 text-white" />
                </div>
              </div>
            </div>
            <h1 className="text-2xl font-bold mb-2">Set New Password</h1>
            <p className="text-sm text-muted-foreground">
              Choose a strong password for your account
            </p>
          </div>

          {/* Reset password form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="password">New Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={isLoading}
                className="bg-muted/50"
              />
              {password && (
                <div className="flex items-center gap-2 text-xs">
                  <div className="flex-1 h-1 bg-muted rounded-full overflow-hidden">
                    <div 
                      className={`h-full transition-all ${
                        passwordStrength.strength === 1 ? 'w-1/4 bg-red-500' :
                        passwordStrength.strength === 2 ? 'w-2/4 bg-orange-500' :
                        passwordStrength.strength === 3 ? 'w-3/4 bg-yellow-500' :
                        'w-full bg-green-500'
                      }`}
                    />
                  </div>
                  <span className={passwordStrength.color}>
                    {passwordStrength.label}
                  </span>
                </div>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirmPassword">Confirm New Password</Label>
              <Input
                id="confirmPassword"
                type="password"
                placeholder="••••••••"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                disabled={isLoading}
                className="bg-muted/50"
              />
              {confirmPassword && (
                <div className="flex items-center gap-1 text-xs">
                  {password === confirmPassword ? (
                    <>
                      <Check className="w-3 h-3 text-green-500" />
                      <span className="text-green-500">Passwords match</span>
                    </>
                  ) : (
                    <>
                      <X className="w-3 h-3 text-red-500" />
                      <span className="text-red-500">Passwords don't match</span>
                    </>
                  )}
                </div>
              )}
            </div>

            {error && (
              <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20">
                <p className="text-sm text-destructive">{error}</p>
              </div>
            )}

            <Button
              type="submit"
              className="w-full"
              variant="hero"
              size="lg"
              disabled={isLoading || !password || password !== confirmPassword}
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Updating password...
                </>
              ) : (
                'Update Password'
              )}
            </Button>
          </form>
        </Card>

        {/* Security tip */}
        <p className="text-center text-xs text-muted-foreground mt-6">
          Use a combination of letters, numbers, and symbols for a strong password
        </p>
      </div>
    </div>
  );
};

export default ResetPassword;

