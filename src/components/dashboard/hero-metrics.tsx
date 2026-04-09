import { Bell, Bookmark, GraduationCap, MapPin } from "lucide-react";

import type { ReturnTypeOfBuildDashboardModel } from "./types";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";

const metricIcons = [Bell, GraduationCap, Bookmark, MapPin];

export function HeroMetrics({ hero }: { hero: ReturnTypeOfBuildDashboardModel["hero"] }) {
  const metrics = [
    { label: "未読", value: `${hero.unreadNotices}件` },
    { label: "授業", value: `${hero.totalClasses}コマ` },
    { label: "重要", value: `${hero.importantNotices}件` },
    { label: "注目", value: `${hero.flaggedNotices}件` },
  ];

  return (
    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      {metrics.map((metric, index) => {
        const Icon = metricIcons[index];

        return (
          <Card key={metric.label} className="border-primary/10 bg-gradient-to-br from-card via-card to-primary/5">
            <CardHeader className="flex-row items-center justify-between pb-3">
              <CardTitle className="text-sm text-muted-foreground">{metric.label}</CardTitle>
              <Icon className="size-4 text-primary" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-semibold tracking-tight">{metric.value}</div>
            </CardContent>
          </Card>
        );
      })}
    </section>
  );
}
