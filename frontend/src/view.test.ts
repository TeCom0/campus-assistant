import { describe, expect, it } from "vitest";
import { viewFromHash } from "./view";

describe("viewFromHash", () => {
  it("opens the About page only for #about", () => {
    expect(viewFromHash("#about")).toBe("about");
  });

  it("shows the chat for no hash, the Chat link's # and a citation's hash", () => {
    expect(["", "#", "#source-2-1"].map(viewFromHash)).toEqual(["chat", "chat", "chat"]);
  });
});
