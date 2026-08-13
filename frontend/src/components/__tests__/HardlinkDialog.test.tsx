import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";
import { api } from "../../api/client";
import type { DestinationRoot, Item } from "../../api/types";
import { HardlinkDialog } from "../HardlinkDialog";

vi.mock("../../api/client", async (importOriginal) => {
  const mod = await importOriginal<typeof import("../../api/client")>();
  return {
    ...mod,
    api: {
      ...mod.api,
      previewHardlink: vi.fn(),
      executeHardlink: vi.fn(),
    },
  };
});

const roots: DestinationRoot[] = [
  { path: "/media/movies", label: "Movies", categories: ["movies"],
    linkable: true, reason: null },
  { path: "/backup", label: "Backup", categories: [], linkable: false,
    reason: "different disk" },
];

const item: Item = {
  name: "Example.Movie.2024",
  rel_path: "Example.Movie.2024",
  is_dir: true,
  total_size: 1,
  file_count: 1,
  category: "movies",
  managed_status: "MANAGED",
  link_status: "UNLINKED",
  non_portable: false,
};

function renderDialog() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <HardlinkDialog item={item} roots={roots} open onClose={() => {}} />
    </QueryClientProvider>,
  );
}

test("preselects root from category and subpath from name", () => {
  renderDialog();
  expect(screen.getByLabelText(/destination/i)).toHaveTextContent("Movies");
  expect(screen.getByLabelText(/subpath/i)).toHaveValue("Example.Movie.2024");
});

test("unlinkable root shows reason and disables preview", async () => {
  renderDialog();
  await userEvent.click(screen.getByLabelText(/destination/i));
  await userEvent.click(screen.getByRole("option", { name: /backup/i }));
  expect(screen.getByText("different disk")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /preview/i })).toBeDisabled();
});

test("collision in preview keeps confirm disabled", async () => {
  vi.mocked(api.previewHardlink).mockResolvedValueOnce({
    dest_path: "/media/movies/Example.Movie.2024",
    will_link: 0,
    will_skip: 0,
    collisions: ["/media/movies/Example.Movie.2024/f.mkv"],
    files: [{ source_rel_path: "f.mkv", dest_path: "x", action: "COLLISION" }],
  });
  renderDialog();
  expect(screen.getByRole("button", { name: /confirm/i })).toBeDisabled();
  await userEvent.click(screen.getByRole("button", { name: /preview/i }));
  expect(await screen.findAllByText(/collision/i)).not.toHaveLength(0);
  expect(screen.getByRole("button", { name: /confirm/i })).toBeDisabled();
});

test("clean preview enables confirm and executes", async () => {
  vi.mocked(api.previewHardlink).mockResolvedValueOnce({
    dest_path: "/media/movies/Example.Movie.2024",
    will_link: 1,
    will_skip: 0,
    collisions: [],
    files: [{ source_rel_path: "f.mkv", dest_path: "x", action: "LINK" }],
  });
  vi.mocked(api.executeHardlink).mockResolvedValueOnce({
    dest_path: "x",
    linked: 1,
    skipped: 0,
    rolled_back: false,
  });
  renderDialog();
  await userEvent.click(screen.getByRole("button", { name: /preview/i }));
  const confirm = await screen.findByRole("button", { name: /confirm/i });
  expect(confirm).toBeEnabled();
  await userEvent.click(confirm);
  expect(api.executeHardlink).toHaveBeenCalledWith(
    {
      source_rel_path: "Example.Movie.2024",
      dest_root: "/media/movies",
      subpath: "Example.Movie.2024",
    },
    expect.anything(),
  );
});

test("editing subpath after preview requires a new preview", async () => {
  vi.mocked(api.previewHardlink).mockResolvedValue({
    dest_path: "/media/movies/Renamed",
    will_link: 1,
    will_skip: 0,
    collisions: [],
    files: [{ source_rel_path: "f.mkv", dest_path: "x", action: "LINK" }],
  });
  renderDialog();
  await userEvent.click(screen.getByRole("button", { name: /preview/i }));
  expect(await screen.findByRole("button", { name: /confirm/i })).toBeEnabled();
  await userEvent.type(screen.getByLabelText(/subpath/i), "-edited");
  expect(screen.getByRole("button", { name: /confirm/i })).toBeDisabled();
});
