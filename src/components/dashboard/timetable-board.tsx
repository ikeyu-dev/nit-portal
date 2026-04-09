import { MapPin, NotebookPen } from "lucide-react";

import type { TimetableEntry } from "../../lib/dashboard";
import { groupTimetableByWeekday } from "../../lib/dashboard";
import { Badge } from "../ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";

export function TimetableBoard({ entries }: { entries: TimetableEntry[] }) {
  const groups = groupTimetableByWeekday(entries);

  return (
    <Card className="overflow-hidden">
      <CardHeader>
        <CardTitle>時間割</CardTitle>
        <CardDescription>曜日ごとにまとまった現在の履修一覧</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {groups.map((group) => (
          <section
            key={group.weekday}
            className="rounded-[24px] border border-border/70 bg-background/80 p-4"
          >
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold">{group.weekday}</h3>
              <Badge variant="secondary">{group.entries.length}コマ</Badge>
            </div>
            <div className="space-y-3">
              {group.entries.map((entry) => (
                <article
                  key={entry.portal_timetable_key}
                  className="rounded-[22px] border border-border/60 bg-card p-4"
                >
                  <div className="mb-2 flex items-center justify-between gap-3">
                    <Badge>{entry.period}限</Badge>
                    <span className="text-xs text-muted-foreground">{entry.credits}</span>
                  </div>
                  <h4 className="text-base font-semibold leading-snug">{entry.subject}</h4>
                  <p className="mt-2 text-sm text-muted-foreground">{entry.instructor}</p>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
                    {entry.room ? (
                      <span className="inline-flex items-center gap-1">
                        <MapPin className="size-3.5" />
                        {entry.room}
                      </span>
                    ) : null}
                    <span className="inline-flex items-center gap-1">
                      <NotebookPen className="size-3.5" />
                      {entry.course_code}
                    </span>
                    {entry.note ? <Badge variant="outline">{entry.note}</Badge> : null}
                  </div>
                </article>
              ))}
            </div>
          </section>
        ))}
      </CardContent>
    </Card>
  );
}
