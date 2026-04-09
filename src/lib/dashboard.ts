export type StatusPayload = {
  metadata: {
    exported_at: string;
    export_user_id: number | null;
  };
  notices: {
    count: number;
    all_tab_count: number;
    exported_at: string;
  };
  timetable: {
    count: number;
    academic_year: number | null;
    semester: string | null;
    campus: string | null;
    exported_at: string;
  };
};

export type TimetableEntry = {
  id: number;
  portal_timetable_key: string;
  academic_year: number;
  semester: string;
  campus: string;
  weekday: string;
  period: string;
  subject: string;
  instructor: string;
  room: string;
  course_code: string;
  credits: string;
  note: string;
  last_synced_at: string;
};

export type TimetablePayload = {
  metadata: {
    count: number;
    academic_year: number | null;
    semester: string | null;
    campus: string | null;
    exported_at: string;
  };
  items: TimetableEntry[];
};

export type NoticeItem = {
  id: number;
  portal_notice_key: string;
  title: string;
  sender: string;
  category: string | null;
  body: string | null;
  published_on: string | null;
  notice_starts_at: string | null;
  notice_ends_at: string | null;
  is_new: boolean;
  is_important: boolean;
  is_flagged: boolean;
  is_read: boolean;
  source_tab_labels: string[];
  detail_link_ids: string[];
  content_hash: string | null;
  first_seen_at: string | null;
  content_updated_at: string | null;
  last_synced_at: string;
  last_seen_at: string | null;
};

export type NoticesPayload = {
  metadata: {
    count: number;
    all_tab_count: number;
    exported_at: string;
  };
  items: NoticeItem[];
};

export type DashboardData = {
  status: StatusPayload;
  timetable: TimetablePayload;
  notices: NoticesPayload;
};

export type NoticeFilter = "all" | "unread" | "important" | "flagged";

const weekdayOrder = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日"];

export function buildDashboardModel(
  status: StatusPayload,
  timetable: TimetablePayload,
  notices: NoticesPayload,
) {
  const unreadNotices = notices.items.filter((item) => !item.is_read).length;
  const importantNotices = notices.items.filter((item) => item.is_important).length;
  const flaggedNotices = notices.items.filter((item) => item.is_flagged).length;

  return {
    hero: {
      totalClasses: timetable.items.length,
      unreadNotices,
      importantNotices,
      flaggedNotices,
      semesterLabel: `${status.timetable.academic_year ?? "-"} ${status.timetable.semester ?? ""}`.trim(),
      campusLabel: status.timetable.campus ?? "-",
      exportedAt: formatRelativeDateLabel(status.metadata.exported_at),
    },
  };
}

export function groupTimetableByWeekday(entries: TimetableEntry[]) {
  const groups = new Map<string, TimetableEntry[]>();

  for (const weekday of weekdayOrder) {
    groups.set(weekday, []);
  }

  for (const entry of entries) {
    const bucket = groups.get(entry.weekday) ?? [];
    bucket.push(entry);
    groups.set(entry.weekday, bucket);
  }

  return [...groups.entries()]
    .map(([weekday, items]) => ({
      weekday,
      entries: [...items].sort((left, right) => Number(left.period) - Number(right.period)),
    }))
    .filter((group) => group.entries.length > 0);
}

export function filterNotices(
  notices: NoticeItem[],
  options: { query: string; filter: NoticeFilter },
) {
  const normalizedQuery = options.query.trim().toLowerCase();

  return notices.filter((notice) => {
    const matchesFilter =
      options.filter === "all" ||
      (options.filter === "unread" && !notice.is_read) ||
      (options.filter === "important" && notice.is_important) ||
      (options.filter === "flagged" && notice.is_flagged);

    if (!matchesFilter) {
      return false;
    }

    if (!normalizedQuery) {
      return true;
    }

    const haystack = [notice.title, notice.sender, notice.category ?? "", notice.body ?? ""]
      .join(" ")
      .toLowerCase();

    return haystack.includes(normalizedQuery);
  });
}

export function formatRelativeDateLabel(value: string | null) {
  if (!value) {
    return "-";
  }

  const date = new Date(value);

  return new Intl.DateTimeFormat("ja-JP", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}
