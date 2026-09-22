import axios from "axios";
import type {
  Analysis,
  AnalysisCreatePayload,
  Chart,
  ChatMessage,
  ChatTurn,
  DataQualityReport,
  Dataset,
  DatasetPreview,
  Health,
  MethodSpec,
  Project,
  ProjectCreatePayload,
  ProjectSummary,
  Recommendation,
  Report,
} from "../types";

const api = axios.create({ baseURL: "/api" });

export function extractErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map((d) => d.msg ?? JSON.stringify(d)).join("; ");
  }
  return "Something went wrong. Please try again.";
}

/** If the backend rejected an Excel upload because it has multiple sheets, returns
 * the list of sheet names to choose from; otherwise returns null. */
export function getSheetSelectionRequired(err: unknown): string[] | null {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (detail && typeof detail === "object" && detail.requires_sheet_selection) {
      return detail.sheets ?? [];
    }
  }
  return null;
}

export const projectsApi = {
  list: () => api.get<ProjectSummary[]>("/projects").then((r) => r.data),
  get: (id: number) => api.get<Project>(`/projects/${id}`).then((r) => r.data),
  create: (payload: ProjectCreatePayload) =>
    api.post<Project>("/projects", payload).then((r) => r.data),
};

export const datasetsApi = {
  listForProject: (projectId: number) =>
    api.get<Dataset[]>(`/projects/${projectId}/datasets`).then((r) => r.data),
  upload: (projectId: number, file: File, sheetName?: string) => {
    const form = new FormData();
    form.append("file", file);
    if (sheetName) form.append("sheet_name", sheetName);
    return api
      .post<Dataset>(`/projects/${projectId}/datasets`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data);
  },
  preview: (datasetId: number, offset = 0, limit = 50) =>
    api
      .get<DatasetPreview>(`/datasets/${datasetId}/preview`, { params: { offset, limit } })
      .then((r) => r.data),
  quality: (datasetId: number) =>
    api.get<DataQualityReport>(`/datasets/${datasetId}/quality`).then((r) => r.data),
};

export const methodsApi = {
  list: () => api.get<MethodSpec[]>("/methods").then((r) => r.data),
};

export const analysesApi = {
  listForProject: (projectId: number) =>
    api.get<Analysis[]>(`/projects/${projectId}/analyses`).then((r) => r.data),
  create: (projectId: number, payload: AnalysisCreatePayload) =>
    api.post<Analysis>(`/projects/${projectId}/analyses`, payload).then((r) => r.data),
  get: (analysisId: number) =>
    api.get<Analysis>(`/analyses/${analysisId}`).then((r) => r.data),
  rerun: (analysisId: number) =>
    api.post<Analysis>(`/analyses/${analysisId}/rerun`).then((r) => r.data),
  interpret: (analysisId: number) =>
    api.post<Analysis>(`/analyses/${analysisId}/interpret`).then((r) => r.data),
  remove: (analysisId: number) => api.delete(`/analyses/${analysisId}`).then((r) => r.data),
};

export const chartsApi = {
  imageUrl: (chartId: number) => `/api/charts/${chartId}`,
  listForAnalysis: (analysisId: number) =>
    api.get<Chart[]>(`/analyses/${analysisId}/charts`).then((r) => r.data),
  create: (analysisId: number, kind?: string) =>
    api.post<Chart>(`/analyses/${analysisId}/charts`, { kind }).then((r) => r.data),
};

export const recommendationsApi = {
  forProject: (projectId: number, datasetId?: number) =>
    api
      .post<Recommendation[]>(`/projects/${projectId}/recommendations`, null, {
        params: datasetId ? { dataset_id: datasetId } : undefined,
      })
      .then((r) => r.data),
};

export const chatApi = {
  history: (projectId: number) =>
    api.get<ChatMessage[]>(`/projects/${projectId}/chat`).then((r) => r.data),
  send: (projectId: number, datasetId: number, message: string) =>
    api
      .post<ChatTurn>(`/projects/${projectId}/chat`, { dataset_id: datasetId, message })
      .then((r) => r.data),
};

export const healthApi = {
  get: () => api.get<Health>("/health").then((r) => r.data),
};

export const reportsApi = {
  list: (projectId: number) =>
    api.get<Report[]>(`/projects/${projectId}/reports`).then((r) => r.data),
  create: (projectId: number, format: "html" | "docx", analysisIds?: number[]) =>
    api
      .post<Report>(`/projects/${projectId}/reports`, {
        format,
        analysis_ids: analysisIds && analysisIds.length ? analysisIds : null,
      })
      .then((r) => r.data),
  downloadUrl: (reportId: number) => `/api/reports/${reportId}/download`,
  fetchHtml: (reportId: number) =>
    api.get(`/reports/${reportId}/download`, { responseType: "text" }).then((r) => r.data as string),
};
