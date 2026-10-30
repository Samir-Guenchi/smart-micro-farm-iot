import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { setToken } from "./api";
import { timeAgo } from "./format";
import i18n from "./i18n";
import { mockFetch } from "./mock/server";

beforeEach(() => {
  localStorage.clear();
  window.location.hash = "";
});
afterEach(() => vi.restoreAllMocks());

describe("dashboard", () => {
  it("signs in and shows one card per node with status", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.type(screen.getByLabelText("Username"), "farmer");
    await user.type(screen.getByLabelText("Password"), "pw");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    const bed = await screen.findByTestId("node-irrigation-1");
    expect(within(bed).getByText("Irrigation · Bed 1")).toBeInTheDocument();
    expect(within(bed).getByText("Online")).toBeInTheDocument();
    expect(within(bed).getByText("Soil moisture")).toBeInTheDocument();
    expect(within(screen.getByTestId("node-coop-1")).getByText("Offline")).toBeInTheDocument();
    expect(screen.getByTestId("node-hive-1")).toBeInTheDocument();
  });

  it("waters the bed with the chosen duration after confirming", async () => {
    setToken("mock-token");
    window.location.hash = "#/bed";
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const user = userEvent.setup();
    render(<App />);
    await user.click(await screen.findByText("15 minutes"));
    await user.click(screen.getByRole("button", { name: /Water now/ }));
    expect(window.confirm).toHaveBeenCalledWith("Water bed 1 for 15 min?");
    expect(await screen.findByRole("status")).toHaveTextContent("Watering started for 15 min.");
    expect(await screen.findByRole("img", { name: /Soil moisture/ })).toBeInTheDocument();
  });

  it("does nothing when the farmer cancels", async () => {
    setToken("mock-token");
    window.location.hash = "#/bed";
    vi.spyOn(window, "confirm").mockReturnValue(false);
    const user = userEvent.setup();
    render(<App />);
    await user.click(await screen.findByRole("button", { name: /Water now/ }));
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("shows the coop door state and today's times", async () => {
    setToken("mock-token");
    window.location.hash = "#/coop";
    render(<App />);
    await waitFor(() => expect(screen.getByTestId("door-state")).not.toHaveTextContent("Unknown"));
  });
});

describe("i18n", () => {
  it("switches the page to right-to-left for Arabic", async () => {
    await act(() => i18n.changeLanguage("ar"));
    expect(document.documentElement.dir).toBe("rtl");
    expect(document.documentElement.lang).toBe("ar");
    await act(() => i18n.changeLanguage("en"));
    expect(document.documentElement.dir).toBe("ltr");
  });

  it("formats relative times", () => {
    const t = i18n.t.bind(i18n);
    expect(timeAgo(1000 - 30, t, 1000)).toBe("just now");
    expect(timeAgo(1000 - 5 * 60, t, 1000)).toBe("5 min ago");
    expect(timeAgo(null, t, 1000)).toBe("never");
  });
});

describe("mock API", () => {
  const auth = { headers: { Authorization: "Bearer mock-token" } };

  it("follows the API contract shapes", async () => {
    const nodes = await (await mockFetch("/api/nodes", auth)).json();
    expect(nodes.map((n: { id: string }) => n.id)).toEqual(["irrigation-1", "hive-1", "coop-1"]);
    const readings = await (await mockFetch("/api/readings?node=irrigation-1&metric=soil_moisture_pct&from=0&to=3600", auth)).json();
    expect(readings[0]).toEqual({ ts: expect.any(Number), value: expect.any(Number) });
    expect((await mockFetch("/api/nodes")).status).toBe(401);
  });

  it("caps pump duration like the real API", async () => {
    const res = await mockFetch("/api/nodes/irrigation-1/pump", { ...auth, method: "POST", body: JSON.stringify({ duration_s: 5000 }) });
    expect(res.status).toBe(202);
    expect(await res.json()).toEqual({ ok: true, duration_s: 900 });
  });
});
