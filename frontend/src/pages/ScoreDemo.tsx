import { Card } from "@/components/ui/card";
import { AIScoreDisplay } from "@/components/AIScoreDisplay";

const RecentClips = () => {
  // Mock data for demonstration
  const featuredClip = {
    score: 0.91,
    breakdown: {
      audioEnergy: 0.88,
      pitchVariance: 0.72,
      emotionScore: 0.85,
      keywordBoost: 0.68
    }
  };

  return (
    <div className="container mx-auto px-6 py-8">
      <h2 className="text-2xl font-bold mb-6">AI Score Analysis Demo</h2>
      
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
              score={0.68}
              size="md"
            />
          </div>
        </Card>
      </div>
    </div>
  );
};

export default RecentClips;
