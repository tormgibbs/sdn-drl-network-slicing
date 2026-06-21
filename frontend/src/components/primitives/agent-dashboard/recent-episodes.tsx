import { Card, CardContent } from "#/components/ui/card";
import { Progress } from "#/components/ui/progress";
import type { EpisodeData } from "#/types/agent-dashboard.tsx";

type RecentEpisodesProps = {
  episodes: EpisodeData[];
};

export function RecentEpisodes({ episodes }: RecentEpisodesProps) {
  return (
    <Card className="bg-muted border-none rounded-none">
      <CardContent className="pt-6">
        <p className="text-xs uppercase tracking-widest text-muted-foreground mb-4">
          Recent Episodes
        </p>
        <div className="space-y-3">
          {episodes.map((ep) => {
            const isPositive = ep.reward >= 0;
            return (
              <div key={ep.episode} className="flex items-center gap-3">
                <span className="text-xs font-mono text-muted-foreground w-14 shrink-0">
                  EP {ep.episode}
                </span>
                <Progress value={ep.sla_pct} className="flex-1" />
                <span
                  className={`text-xs font-mono font-bold w-12 text-right ${isPositive ? "text-green-500" : "text-red-500"}`}
                >
                  {isPositive ? "+" : ""}
                  {ep.reward.toFixed(2)}
                </span>
                <span
                  className={`text-xs font-mono w-8 text-right ${ep.sla_pct >= 90 ? "text-green-500" : ep.sla_pct < 70 ? "text-red-500" : ""}`}
                >
                  {ep.sla_pct}%
                </span>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
