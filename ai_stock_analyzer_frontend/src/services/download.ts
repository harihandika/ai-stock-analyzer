import { apiClient } from "@/services/api";

export async function downloadResult(
  path: string,
  filename: string,
  options?: { signal?: AbortSignal; isCurrent?: () => boolean },
) {
  const response = await apiClient.get(path, {
    responseType: "blob",
    signal: options?.signal,
  });
  if (options?.signal?.aborted || (options?.isCurrent && !options.isCurrent()))
    return;
  const url = URL.createObjectURL(response.data);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
