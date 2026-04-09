import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { CalendarClock, RefreshCcw, Siren } from "lucide-react";

import { HeroMetrics } from "./components/dashboard/hero-metrics";
import { NoticeList } from "./components/dashboard/notice-list";
import { TimetableBoard } from "./components/dashboard/timetable-board";
import { Badge } from "./components/ui/badge";
import { Button } from "./components/ui/button";
import { Card, CardContent } from "./components/ui/card";
import type { DashboardData } from "./lib/dashboard";
import { buildDashboardModel } from "./lib/dashboard";
import { loadDashboardData } from "./lib/data";

type AppProps = {
  initialData?: DashboardData;
};

export function App({ initialData }: AppProps) {
  const [data, setData] = useState<DashboardData | null>(initialData ?? null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(!initialData);

  useEffect(() => {
    if (initialData) {
      return;
    }

    let mounted = true;

    loadDashboardData()
      .then((payload) => {
        if (!mounted) {
          return;
        }
        setData(payload);
        setLoading(false);
      })
      .catch((reason: unknown) => {
        if (!mounted) {
          return;
        }
        setError(reason instanceof Error ? reason.message : "Failed to load dashboard data");
        setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [initialData]);

  if (loading) {
    return <Shell>データを読み込んでいます…</Shell>;
  }

  if (error || !data) {
    return (
      <Shell>
        <Card>
          <CardContent className="flex min-h-64 flex-col items-center justify-center gap-4 py-12 text-center">
            <Siren className="size-10 text-chart-3" />
            <div>
              <p className="text-lg font-semibold">ダッシュボードを読み込めませんでした。</p>
              <p className="mt-2 text-sm text-muted-foreground">{error ?? "不明なエラーです。"}</p>
            </div>
          </CardContent>
        </Card>
      </Shell>
    );
  }

  const model = buildDashboardModel(data.status, data.timetable, data.notices);

  return (
    <Shell>
      <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <Card className="border-primary/15 bg-[radial-gradient(circle_at_top_left,_rgba(13,148,136,0.14),_transparent_42%),linear-gradient(135deg,rgba(255,255,255,0.92),rgba(242,255,252,0.86))]">
          <CardContent className="flex flex-col gap-8 pt-8">
            <div className="flex flex-wrap items-center gap-3">
              <Badge>NIT Portal Dashboard</Badge>
              <Badge variant="outline">{model.hero.semesterLabel}</Badge>
              <Badge variant="secondary">{model.hero.campusLabel}</Badge>
            </div>
            <div className="max-w-2xl">
              <h1 className="text-balance text-4xl font-semibold tracking-tight text-foreground md:text-5xl">
                NIT-Portalで、時間割とお知らせをひと目で追う。
              </h1>
              <p className="mt-4 max-w-xl text-sm leading-7 text-muted-foreground md:text-base">
                静的 JSON を読み込むだけの軽量構成で、現在の履修状況と重要通知をひとつの画面に集約します。
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Button type="button" onClick={() => window.location.reload()}>
                <RefreshCcw className="mr-2 size-4" />
                再読み込み
              </Button>
              <Button type="button" variant="outline">
                <CalendarClock className="mr-2 size-4" />
                最終更新 {model.hero.exportedAt}
              </Button>
            </div>
          </CardContent>
        </Card>
        <HeroMetrics hero={model.hero} />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <TimetableBoard entries={data.timetable.items} />
        <NoticeList notices={data.notices.items} />
      </section>
    </Shell>
  );
}

function Shell({ children }: { children: ReactNode }) {
  return (
    <main className="min-h-screen bg-background text-foreground">
      <div className="mx-auto max-w-[1440px] px-4 py-6 sm:px-6 lg:px-8">
        <div className="absolute inset-0 -z-10 bg-grid bg-[size:42px_42px] opacity-60" />
        <div className="absolute inset-x-0 top-0 -z-10 h-[420px] bg-[radial-gradient(circle_at_top,rgba(15,118,110,0.18),transparent_58%)]" />
        <div className="space-y-6">{children}</div>
      </div>
    </main>
  );
}
