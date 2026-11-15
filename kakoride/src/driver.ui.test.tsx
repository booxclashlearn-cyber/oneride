// @vitest-environment jsdom
import {afterEach, describe, expect, it} from "vitest";
import {cleanup, render, screen} from "@testing-library/react";
import DemandCards from "./components/DemandCards";
import type {Demand} from "./types";
afterEach(cleanup);
const data = {passengers: 3, waitingStops: 1, offeredMinor: 6500, groups: [{stopId: "kamwala", name: "Kamwala", passengers: 3, offeredMinor: 6500, destinations: [{stopId: "town", name: "Town Centre", passengers: 3, offeredMinor: 6500, minFareMinor: 2000, maxFareMinor: 2500}]}]} as Demand;
describe("aggregate-only driver view", () => {
  it("shows totals and destination breakdown as offered fares", () => {render(<DemandCards data={data} live/>); expect(screen.getByText("Kamwala")).toBeTruthy(); expect(screen.getByText("Town Centre")).toBeTruthy(); expect(screen.getByText("Passenger budgets · not earnings")).toBeTruthy(); expect(screen.getAllByText("K65").length).toBe(3);});
  it("hides expired or disconnected totals", () => {render(<DemandCards data={data} live={false}/>); expect(screen.queryByText("Kamwala")).toBeNull(); expect(screen.getByText("Waiting for a fresh snapshot")).toBeTruthy();});
  it("shows an honest zero-demand state", () => {render(<DemandCards data={{...data, groups: []}} live/>); expect(screen.getByText("No passengers waiting ahead")).toBeTruthy();});
});
