import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { 
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ChevronDown, Eye, EyeOff, CheckCircle2, XCircle } from "lucide-react";
import { useState } from "react";

const Settings = () => {
  const [threshold, setThreshold] = useState([0.30]);
  const [audioWeight, setAudioWeight] = useState([0.35]);
  const [pitchWeight, setPitchWeight] = useState([0.25]);
  const [emotionWeight, setEmotionWeight] = useState([0.40]);
  const [keywordBoost, setKeywordBoost] = useState([0.15]);
  const [showApiKeys, setShowApiKeys] = useState<Record<string, boolean>>({});

  const totalWeight = audioWeight[0] + pitchWeight[0] + emotionWeight[0] + keywordBoost[0];

  return (
    <div className="container mx-auto px-6 py-8 max-w-5xl space-y-8">
      <h1 className="text-3xl font-bold">⚙️ Settings</h1>

      {/* AI Tuning Section */}
      <Card className="p-6 bg-card border-border">
        <h2 className="text-xl font-semibold mb-6">AI Detection Settings</h2>
        
        <div className="space-y-8">
          {/* Interest Threshold */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <Label className="text-base">Interest Detection Threshold</Label>
              <span className="text-2xl font-bold text-primary">{threshold[0].toFixed(2)}</span>
            </div>
            <Slider 
              value={threshold}
              onValueChange={setThreshold}
              min={0}
              max={1}
              step={0.01}
              className="mb-2"
            />
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <span>Lower (more clips)</span>
              <span>Higher (fewer clips)</span>
            </div>
            <p className="text-sm text-muted-foreground mt-2">
              Currently captures ~{Math.round((1 - threshold[0]) * 50)}% of segments
            </p>
          </div>

          {/* Weight Configuration */}
          <div>
            <h3 className="text-base font-semibold mb-4">Weight Configuration</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <Label>Audio Energy Weight</Label>
                  <span className="text-sm font-mono">{audioWeight[0].toFixed(2)}</span>
                </div>
                <Slider value={audioWeight} onValueChange={setAudioWeight} min={0} max={1} step={0.05} />
                <div className="mt-2 bg-muted rounded-full h-2">
                  <div className="h-full bg-success rounded-full" style={{ width: `${audioWeight[0] * 100}%` }} />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <Label>Pitch Variance Weight</Label>
                  <span className="text-sm font-mono">{pitchWeight[0].toFixed(2)}</span>
                </div>
                <Slider value={pitchWeight} onValueChange={setPitchWeight} min={0} max={1} step={0.05} />
                <div className="mt-2 bg-muted rounded-full h-2">
                  <div className="h-full bg-info rounded-full" style={{ width: `${pitchWeight[0] * 100}%` }} />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <Label>Emotion Weight</Label>
                  <span className="text-sm font-mono">{emotionWeight[0].toFixed(2)}</span>
                </div>
                <Slider value={emotionWeight} onValueChange={setEmotionWeight} min={0} max={1} step={0.05} />
                <div className="mt-2 bg-muted rounded-full h-2">
                  <div className="h-full bg-primary rounded-full" style={{ width: `${emotionWeight[0] * 100}%` }} />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <Label>Keyword Boost</Label>
                  <span className="text-sm font-mono">{keywordBoost[0].toFixed(2)}</span>
                </div>
                <Slider value={keywordBoost} onValueChange={setKeywordBoost} min={0} max={1} step={0.05} />
                <div className="mt-2 bg-muted rounded-full h-2">
                  <div className="h-full bg-warning rounded-full" style={{ width: `${keywordBoost[0] * 100}%` }} />
                </div>
              </div>
            </div>

            <div className="mt-6 p-4 bg-muted/50 rounded-lg">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Total Weight:</span>
                <span className={`text-lg font-bold ${Math.abs(totalWeight - 1.0) < 0.01 ? 'text-success' : 'text-destructive'}`}>
                  {totalWeight.toFixed(2)} {Math.abs(totalWeight - 1.0) < 0.01 ? '✓' : '✗'}
                </span>
              </div>
            </div>
          </div>

          <Button className="w-full bg-primary hover:bg-primary/90">
            Save AI Settings
          </Button>
        </div>
      </Card>

      {/* Stream Settings */}
      <Card className="p-6 bg-card border-border">
        <h2 className="text-xl font-semibold mb-6">Stream Settings</h2>
        
        <div className="space-y-6">
          <div>
            <Label className="mb-3 block">Segment Duration</Label>
            <div className="flex gap-3">
              {['30s', '60s'].map((duration) => (
                <Button
                  key={duration}
                  variant={duration === '30s' ? 'default' : 'outline'}
                  className="flex-1"
                >
                  {duration}
                </Button>
              ))}
            </div>
          </div>

          <div>
            <Label htmlFor="quality">Video Quality</Label>
            <Select defaultValue="720p60">
              <SelectTrigger id="quality">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1080p60">1080p60 (Best Quality)</SelectItem>
                <SelectItem value="720p60">720p60 (Balanced)</SelectItem>
                <SelectItem value="480p">480p (Fast)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label htmlFor="buffer">Buffer Size (clips before merge)</Label>
            <Input id="buffer" type="number" defaultValue={5} min={1} max={10} />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <Label>Auto-restart on error</Label>
              <p className="text-sm text-muted-foreground">Automatically restart monitors if they crash</p>
            </div>
            <Switch defaultChecked />
          </div>
        </div>
      </Card>

      {/* Storage Management */}
      <Card className="p-6 bg-card border-border">
        <h2 className="text-xl font-semibold mb-6">Storage Management</h2>
        
        <div className="space-y-6">
          <div>
            <Label htmlFor="quota">Storage Quota (GB)</Label>
            <Input id="quota" type="number" defaultValue={100} />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <Label>Auto-cleanup old clips</Label>
              <p className="text-sm text-muted-foreground">Delete clips older than specified days</p>
            </div>
            <div className="flex items-center gap-3">
              <Input type="number" defaultValue={30} className="w-20" />
              <span className="text-sm text-muted-foreground">days</span>
              <Switch defaultChecked />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <Label>Current Usage</Label>
              <span className="text-sm font-semibold">48.2 GB / 100 GB</span>
            </div>
            <div className="w-full bg-muted rounded-full h-3">
              <div className="h-full bg-gradient-to-r from-primary to-pink-500 rounded-full" style={{ width: '48%' }} />
            </div>
          </div>

          <Button variant="destructive" className="w-full">
            Clean Up Old Clips Now
          </Button>
        </div>
      </Card>

      {/* API Configuration */}
      <Collapsible>
        <Card className="p-6 bg-card border-border">
          <CollapsibleTrigger className="w-full">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold">API Configuration</h2>
              <ChevronDown className="w-5 h-5" />
            </div>
          </CollapsibleTrigger>
          
          <CollapsibleContent className="mt-6 space-y-4">
            {[
              { name: 'Supabase', key: 'sk-supabase-xxxxx', connected: true },
              { name: 'OpenAI', key: 'sk-proj-xxxxx', connected: true },
              { name: 'Twitch', key: 'twitch-xxxxx', connected: false },
            ].map((api) => (
              <div key={api.name} className="flex items-center gap-4 p-4 bg-muted/50 rounded-lg">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="font-semibold">{api.name}</span>
                    {api.connected ? (
                      <CheckCircle2 className="w-4 h-4 text-success" />
                    ) : (
                      <XCircle className="w-4 h-4 text-destructive" />
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <Input 
                      type={showApiKeys[api.name] ? 'text' : 'password'}
                      value={api.key}
                      readOnly
                      className="flex-1 font-mono text-sm"
                    />
                    <Button
                      size="icon"
                      variant="outline"
                      onClick={() => setShowApiKeys(prev => ({ ...prev, [api.name]: !prev[api.name] }))}
                    >
                      {showApiKeys[api.name] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </Button>
                  </div>
                </div>
                <Button variant="outline">Test</Button>
              </div>
            ))}
          </CollapsibleContent>
        </Card>
      </Collapsible>

      {/* Notifications */}
      <Card className="p-6 bg-card border-border">
        <h2 className="text-xl font-semibold mb-6">Notifications</h2>
        
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <Label>Email alerts</Label>
            <Switch defaultChecked />
          </div>

          <div>
            <Label htmlFor="webhook">Webhook URL (Slack/Discord)</Label>
            <Input id="webhook" placeholder="https://hooks.slack.com/..." />
          </div>

          <div className="space-y-3 pt-4">
            <Label className="text-base">Alert Preferences</Label>
            {[
              { label: 'High-score clips (>0.7)', checked: true },
              { label: 'Upload failures', checked: true },
              { label: 'Storage warnings', checked: true },
              { label: 'Every clip captured', checked: false },
            ].map((pref) => (
              <div key={pref.label} className="flex items-center justify-between">
                <Label className="font-normal">{pref.label}</Label>
                <Switch defaultChecked={pref.checked} />
              </div>
            ))}
          </div>
        </div>
      </Card>
    </div>
  );
};

export default Settings;
