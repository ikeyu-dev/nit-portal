import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { App } from "./App";
import { noticesFixture, statusFixture, timetableFixture } from "./test/fixtures";

describe("App", () => {
  it("renders hero metrics from loaded payloads", async () => {
    render(
      <App
        initialData={{
          status: statusFixture,
          timetable: timetableFixture,
          notices: noticesFixture,
        }}
      />,
    );

    expect(screen.getByText("NIT Portal Dashboard")).toBeInTheDocument();
    expect(screen.getAllByText("未読").length).toBeGreaterThan(0);
    expect(screen.getByText("2件")).toBeInTheDocument();
    expect(screen.getAllByText("授業").length).toBeGreaterThan(0);
    expect(screen.getByText("3コマ")).toBeInTheDocument();
  });

  it("filters notices from the search box", async () => {
    const user = userEvent.setup();

    render(
      <App
        initialData={{
          status: statusFixture,
          timetable: timetableFixture,
          notices: noticesFixture,
        }}
      />,
    );

    await user.type(screen.getByPlaceholderText("お知らせを検索"), "献血");

    expect(screen.getByText("献血実施のお知らせ")).toBeInTheDocument();
    expect(screen.queryByText("TOEICを受験しましょう")).not.toBeInTheDocument();
  });
});
