import type { JobStatus } from "../../../lib/contracts";

export const JOB_STATUS_NAMES: Record<JobStatus, string> = {
  AWAITING_OWNER_APPROVAL: "等待所有者批准",
  QUEUED: "等待执行",
  PREPARING: "准备中",
  EXECUTING: "执行中",
  FINALIZING: "收束中",
  COMPLETED: "已完成",
  COMPLETED_WITH_ERRORS: "部分出错",
  FAILED: "失败",
  REJECTED: "已拒绝",
  CANCEL_REQUESTED: "取消请求中",
  CANCELED: "已取消",
};
