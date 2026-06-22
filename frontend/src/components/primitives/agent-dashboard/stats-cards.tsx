import { Card, CardContent } from "#/components/ui/card";
import { TrendingUp } from "lucide-react";

type StatCardsProps = {
  rewardSignal: number;
  slaSatisfaction: number;
  episodesTrained: number;
  violations: number;
};

export function StatCards({
  rewardSignal,
  slaSatisfaction,
  episodesTrained,
  violations,
}: StatCardsProps) {
  return (
    <div className="grid grid-cols-4 gap-4">
      <Card className="bg-muted border-none rounded-none">
        <CardContent className="pt-6">
          <p className="text-xs uppercase tracking-widest text-muted-foreground mb-2">
            Reward Signal
          </p>
          <p className="text-3xl font-bold text-green-500 flex items-center gap-2">
            {rewardSignal >= 0 ? "+" : ""}
            {rewardSignal.toFixed(2)}
            <TrendingUp size={20} />
          </p>
          <p className="text-xs text-muted-foreground mt-1">current episode</p>
        </CardContent>
      </Card>

      <Card className="bg-muted border-none rounded-none">
        <CardContent className="pt-6">
          <p className="text-xs uppercase tracking-widest text-muted-foreground mb-2">
            SLA Satisfaction
          </p>
          <p className="text-3xl font-bold">{slaSatisfaction.toFixed(1)}%</p>
          <p className="text-xs text-muted-foreground mt-1">last 60 cycles</p>
        </CardContent>
      </Card>

      <Card className="bg-muted border-none rounded-none">
        <CardContent className="pt-6">
          <p className="text-xs uppercase tracking-widest text-muted-foreground mb-2">
            Episodes Trained
          </p>
          <p className="text-3xl font-bold">
            {episodesTrained.toLocaleString()}
          </p>
          <p className="text-xs text-muted-foreground mt-1">PPO · γ=0.99</p>
        </CardContent>
      </Card>

      <Card className="bg-muted border-none rounded-none">
        <CardContent className="pt-6">
          <p className="text-xs uppercase tracking-widest text-muted-foreground mb-2">
            Violations
          </p>
          <p className="text-3xl font-bold text-red-500">{violations}</p>
          <p className="text-xs text-muted-foreground mt-1">last 60 cycles</p>
        </CardContent>
      </Card>
    </div>
  );
}
