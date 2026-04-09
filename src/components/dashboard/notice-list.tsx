import { useDeferredValue, useState } from "react";
import { BellRing, Search } from "lucide-react";

import type { NoticeFilter, NoticeItem } from "../../lib/dashboard";
import { filterNotices, formatRelativeDateLabel } from "../../lib/dashboard";
import { Badge } from "../ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Input } from "../ui/input";
import { ScrollArea } from "../ui/scroll-area";
import { Tabs, TabsList, TabsTrigger } from "../ui/tabs";

const filterLabels: Record<NoticeFilter, string> = {
  all: "すべて",
  unread: "未読",
  important: "重要",
  flagged: "注目",
};

export function NoticeList({ notices }: { notices: NoticeItem[] }) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<NoticeFilter>("all");
  const deferredQuery = useDeferredValue(query);
  const filtered = filterNotices(notices, { query: deferredQuery, filter });

  return (
    <Card className="overflow-hidden">
      <CardHeader>
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <CardTitle>お知らせ</CardTitle>
            <CardDescription>検索と状態フィルタで必要な通知だけを絞り込み</CardDescription>
          </div>
          <div className="w-full max-w-md">
            <div className="relative">
              <Search className="pointer-events-none absolute left-4 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="お知らせを検索"
                className="pl-10"
              />
            </div>
          </div>
        </div>
        <Tabs value={filter} onValueChange={(value) => setFilter(value as NoticeFilter)}>
          <TabsList>
            {Object.entries(filterLabels).map(([value, label]) => (
              <TabsTrigger key={value} value={value}>
                {label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[520px] pr-4">
          <div className="space-y-3">
            {filtered.map((notice) => (
              <article
                key={notice.portal_notice_key}
                className="rounded-[24px] border border-border/70 bg-background/80 p-5"
              >
                <div className="mb-3 flex flex-wrap items-center gap-2">
                  {notice.is_new ? <Badge>NEW</Badge> : null}
                  {notice.is_important ? <Badge variant="warn">重要</Badge> : null}
                  {notice.is_flagged ? <Badge variant="outline">注目</Badge> : null}
                  {!notice.is_read ? <Badge variant="secondary">未読</Badge> : null}
                </div>
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h3 className="text-lg font-semibold leading-snug">{notice.title}</h3>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {notice.sender} · {notice.published_on ?? "-"}
                    </p>
                  </div>
                  <BellRing className="mt-1 size-5 shrink-0 text-primary" />
                </div>
                {notice.body ? <p className="mt-4 line-clamp-3 text-sm leading-6 text-foreground/90">{notice.body}</p> : null}
                <div className="mt-4 flex flex-wrap gap-2 text-xs text-muted-foreground">
                  {notice.category ? <Badge variant="outline">{notice.category}</Badge> : null}
                  <span>更新: {formatRelativeDateLabel(notice.content_updated_at)}</span>
                  <span>同期: {formatRelativeDateLabel(notice.last_synced_at)}</span>
                </div>
              </article>
            ))}
            {filtered.length === 0 ? (
              <div className="rounded-[24px] border border-dashed border-border bg-background/70 p-8 text-center text-sm text-muted-foreground">
                条件に一致するお知らせはありません。
              </div>
            ) : null}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
