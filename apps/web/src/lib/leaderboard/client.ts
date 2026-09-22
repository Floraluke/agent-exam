import { request } from "../api-client";
import { leaderboardPage, type LeaderboardPage } from "./shapes";

export type LeaderboardFilters = {
  datasetId: string; datasetRevision: string; split: string;
  repo: string; toolProfileId: string;
};

// 预填用的 URL 查询参数名与排行榜 HTTP 查询名同形，便于与接口文档对照。
// 只读：调用方不回写这些参数，URL 保持用户可分享的原样。
export function filtersFromQuery(query: URLSearchParams): LeaderboardFilters {
  return {
    datasetId: query.get("dataset_id") ?? "",
    datasetRevision: query.get("dataset_revision") ?? "",
    split: query.get("split") ?? "",
    repo: query.get("repo") ?? "",
    toolProfileId: query.get("tool_profile_id") ?? "",
  };
}

// 从其它页面进入排行榜的链接目标；空值不进 URL，缺参时表单对应留空。
export function leaderboardHref(filters: LeaderboardFilters): string {
  const query = new URLSearchParams({ view: "leaderboard" });
  if (filters.datasetId) query.set("dataset_id", filters.datasetId);
  if (filters.datasetRevision) query.set("dataset_revision", filters.datasetRevision);
  if (filters.split) query.set("split", filters.split);
  if (filters.repo) query.set("repo", filters.repo);
  if (filters.toolProfileId) query.set("tool_profile_id", filters.toolProfileId);
  return `/?${query.toString()}`;
}

export async function leaderboard(
  filters: LeaderboardFilters, cursor?: string,
): Promise<LeaderboardPage> {
  const query = new URLSearchParams({
    evaluation_track: "closed_book", dataset_id: filters.datasetId,
    dataset_revision: filters.datasetRevision, split: filters.split, limit: "20",
  });
  if (filters.repo) query.set("repo", filters.repo);
  if (filters.toolProfileId) query.set("tool_profile_id", filters.toolProfileId);
  if (cursor) query.set("cursor", cursor);
  return leaderboardPage(await request("leaderboard?" + query));
}
