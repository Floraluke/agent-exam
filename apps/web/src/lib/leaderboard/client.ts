import { request } from "../api-client";
import { leaderboardPage, type LeaderboardPage } from "./shapes";

export type LeaderboardFilters = {
  datasetId: string; datasetRevision: string; split: string;
  repo: string; toolProfileId: string;
};

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
