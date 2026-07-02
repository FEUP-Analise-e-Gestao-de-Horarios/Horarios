import { describe, expect, it } from "vitest";
import { PROJECT_NAME_MAX_LENGTH, validateProjectName } from "./projectName";

describe("validateProjectName", () => {
  it("accepts allowed characters", () => {
    expect(validateProjectName("Horario 2024")).toBeNull();
    expect(validateProjectName("MIEIC_1-2:A")).toBeNull();
    expect(validateProjectName("abcXYZ0123")).toBeNull();
  });

  it("rejects empty or whitespace-only names", () => {
    expect(validateProjectName("")).not.toBeNull();
    expect(validateProjectName("   ")).not.toBeNull();
  });

  it("rejects names longer than the max length", () => {
    expect(validateProjectName("a".repeat(PROJECT_NAME_MAX_LENGTH))).toBeNull();
    expect(validateProjectName("a".repeat(PROJECT_NAME_MAX_LENGTH + 1))).not.toBeNull();
  });

  it("rejects disallowed characters", () => {
    expect(validateProjectName("nome!")).not.toBeNull();
    expect(validateProjectName("olá")).not.toBeNull();
    expect(validateProjectName("a/b")).not.toBeNull();
    expect(validateProjectName("a.b")).not.toBeNull();
  });
});
