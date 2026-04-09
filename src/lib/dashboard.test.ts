import { describe, expect, it } from "vitest";

import { noticesFixture, statusFixture, timetableFixture } from "../test/fixtures";
import {
  buildDashboardModel,
  filterNotices,
  formatRelativeDateLabel,
  groupTimetableByWeekday,
} from "./dashboard";

describe("dashboard", () => {
  it("builds summary metrics from static payloads", () => {
    const model = buildDashboardModel(statusFixture, timetableFixture, noticesFixture);

    expect(model.hero.totalClasses).toBe(3);
    expect(model.hero.unreadNotices).toBe(2);
    expect(model.hero.flaggedNotices).toBe(1);
    expect(model.hero.semesterLabel).toContain("2026");
  });

  it("groups timetable entries by weekday and sorts by period", () => {
    const groups = groupTimetableByWeekday(timetableFixture.items);

    expect(groups[0].weekday).toBe("月曜日");
    expect(groups[0].entries[0].period).toBe("1");
    expect(groups.at(-1)?.weekday).toBe("金曜日");
  });

  it("filters notices by search text and emphasis state", () => {
    const filtered = filterNotices(noticesFixture.items, {
      query: "toeic",
      filter: "flagged",
    });

    expect(filtered).toHaveLength(1);
    expect(filtered[0].title).toContain("TOEIC");
  });

  it("formats timestamps for compact cards", () => {
    expect(formatRelativeDateLabel("2026-04-09T10:10:29.588054")).toContain("2026");
  });
});
