import { Card } from "@/components/ui/card";
import { AIScoreDisplay } from "@/components/AIScoreDisplay";
import { useClips } from "@/hooks/useClips";
import { clampScore } from "@/lib/utils";

const ScoreDemo = () => {
  // Use real clip data instead of hardcoded values
  const { data: clipsData } = useClips({ limit: 1 });
  const clips = clipsData?.clips || [];
  
  // Use the first clip's data if available, otherwise show placeholder
  const featuredClip = clips.length > 0 && clips[0].confidence_score ? {
    score: clampScore(clips[0].confidence_score),
    breakdown: clips[0].score_breakdown || {
      audioEnergy: 0.0,
      pitchVariance: 0.0,
      emotionScore: 0.0,
      keywordBoost: 0.0
    }
  } : null;

  return (
    <div className="container mx-auto px-6 py-8">
      <h2 className="text-2xl font-bold mb-6">AI Score Analysis Demo</h2>
      
      {featuredClip ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* Large Score Display with Breakdown */}
          <Card className="p-6 glass-strong border-white/10">
            <h3 className="text-lg font-semibold mb-4">Featured Clip Analysis</h3>
            <AIScoreDisplay 
              score={featuredClip.score}
              breakdown={featuredClip.breakdown}
              size="lg"
              showBreakdown={true}
            />
          </Card>

          {/* Medium Score Display */}
          <Card className="p-6 glass-strong border-white/10">
            <h3 className="text-lg font-semibold mb-4">Quick Score View</h3>
            <div className="flex justify-center">
              <AIScoreDisplay 
                score={featuredClip.score}
                size="md"
              />
            </div>
          </Card>
        </div>
      ) : (
        <Card className="p-6 glass-strong border-white/10">
          <p className="text-muted-foreground text-center">
            No clips available. Create some clips to see score analysis.
          </p>
        </Card>
      )}
    </div>
  );
};

export default ScoreDemo;
