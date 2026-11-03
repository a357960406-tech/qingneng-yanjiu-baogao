import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusTag } from "./StatusTag";

describe("StatusTag", () => {
  it("渲染可用状态", () => {
    render(<StatusTag status="可用" />);
    expect(screen.getByText("可用")).toBeInTheDocument();
  });

  it("渲染无文字状态", () => {
    render(<StatusTag status="无文字" />);
    expect(screen.getByText("无文字，检索不到")).toBeInTheDocument();
  });

  it("渲染失败状态", () => {
    render(<StatusTag status="失败" />);
    expect(screen.getByText("失败")).toBeInTheDocument();
  });

  it("未知状态回退显示原文", () => {
    render(<StatusTag status="未知状态" />);
    expect(screen.getByText("未知状态")).toBeInTheDocument();
  });
});
