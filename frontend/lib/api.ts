const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface PolygonGeoJSON {
  type: "Polygon";
  coordinates: number[][][];
}

export interface GeophysicalSurvey {
  id: string;
  name: string;
  survey_type: string;
  created_at: string;
}

export interface GravityStation {
  id: string;
  code: string;
  lon: number;
  lat: number;
  latitude_deg: number;
  elevation_m: number;
  observed_gravity_mgal: number;
}

export interface ResistivitySounding {
  id: string;
  code: string;
  array_type: "wenner" | "schlumberger";
  lon: number;
  lat: number;
}

export interface SeismicLine {
  id: string;
  code: string;
  coordinates: number[][];
}

export interface MethodMeta {
  method: string;
  parameters: Record<string, unknown>;
  uncertainty_note: string;
  limitations: string;
}

export interface BouguerAnomalyResult extends MethodMeta {
  result_id: string;
  station_id: string;
  station_code: string;
  lon: number;
  lat: number;
  normal_gravity_mgal: number;
  free_air_correction_mgal: number;
  bouguer_correction_mgal: number;
  bouguer_anomaly_mgal: number;
  density_kg_m3: number;
}

export interface MagneticRtpResult extends MethodMeta {
  result_id: string;
  shape: [number, number];
  peak_row: number;
  peak_col: number;
  peak_value_nt: number;
  trough_row: number;
  trough_col: number;
  trough_value_nt: number;
  assumed_purely_induced_magnetization: boolean;
  low_inclination_warning: boolean;
  rtp_grid_shape: [number, number];
}

export interface SoundingCurvePoint {
  array_type: string;
  geometric_factor_m: number;
  apparent_resistivity_ohm_m: number;
  estimated_investigation_depth_m: number;
}

export interface ResistivitySoundingResult extends MethodMeta {
  result_id: string;
  sounding_id: string;
  sounding_code: string;
  array_type: string;
  n_readings: number;
  sounding_curve: SoundingCurvePoint[];
  min_apparent_resistivity_ohm_m: number;
  max_apparent_resistivity_ohm_m: number;
  max_investigation_depth_m: number;
}

export interface SeismicRefractionResult extends MethodMeta {
  result_id: string;
  line_id: string;
  line_code: string;
  v1_m_s: number;
  v2_m_s: number;
  critical_angle_deg: number;
  crossover_distance_m: number;
  intercept_time_s: number;
  depth_m: number;
  depth_from_intercept_time_m: number;
  n_direct_points: number;
  n_refracted_points: number;
  direct_branch_residual_rms_s: number;
  refracted_branch_residual_rms_s: number;
}

export interface SeismicReading {
  id: string;
  offset_m: number;
  first_arrival_time_ms: number;
  is_direct_wave: boolean | null;
}

export interface AnomalyPatch {
  patch_id: number;
  n_cells: number;
  area_m2: number;
  centroid_row: number;
  centroid_col: number;
  mean_value: number;
  peak_value: number;
  peak_row: number;
  peak_col: number;
  mean_z_score: number;
}

export interface AnomalyDetectionResult extends MethodMeta {
  result_id: string;
  n_patches: number;
  patches: AnomalyPatch[];
  background_mean: number;
  background_std: number;
  threshold_sigma: number;
  direction: string;
}

export interface ChatToolCall {
  tool: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
}

export interface ChatResponse {
  reply: string;
  tool_calls: ChatToolCall[];
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  listSurveys: () => request<GeophysicalSurvey[]>("/api/v1/surveys"),

  createSurvey: (name: string, boundary: PolygonGeoJSON, surveyType = "multi-metodo") =>
    request<GeophysicalSurvey>("/api/v1/surveys", {
      method: "POST",
      body: JSON.stringify({ name, boundary, survey_type: surveyType }),
    }),

  getSurvey: (surveyId: string) => request<GeophysicalSurvey>(`/api/v1/surveys/${surveyId}`),

  listGravityStations: (surveyId: string) => request<GravityStation[]>(`/api/v1/surveys/${surveyId}/gravity-stations`),

  listResistivitySoundings: (surveyId: string) =>
    request<ResistivitySounding[]>(`/api/v1/surveys/${surveyId}/resistivity-soundings`),

  listSeismicLines: (surveyId: string) => request<SeismicLine[]>(`/api/v1/surveys/${surveyId}/seismic-lines`),

  listSeismicReadings: (lineId: string) => request<SeismicReading[]>(`/api/v1/seismic-lines/${lineId}/readings`),

  calculateBouguerAnomaly: (stationId: string, densityKgM3 = 2670.0) =>
    request<BouguerAnomalyResult>("/api/v1/analysis/bouguer-anomaly", {
      method: "POST",
      body: JSON.stringify({ station_id: stationId, density_kg_m3: densityKgM3 }),
    }),

  calculateMagneticRtp: (
    grid: number[][],
    pixelSizeM: number,
    inclinationDeg: number,
    declinationDeg: number
  ) =>
    request<MagneticRtpResult>("/api/v1/analysis/magnetic-rtp", {
      method: "POST",
      body: JSON.stringify({
        grid,
        pixel_size_m: pixelSizeM,
        inclination_deg: inclinationDeg,
        declination_deg: declinationDeg,
      }),
    }),

  calculateResistivitySounding: (soundingId: string) =>
    request<ResistivitySoundingResult>("/api/v1/analysis/resistivity-sounding", {
      method: "POST",
      body: JSON.stringify({ sounding_id: soundingId }),
    }),

  interpretSeismicRefraction: (lineId: string) =>
    request<SeismicRefractionResult>("/api/v1/analysis/seismic-refraction", {
      method: "POST",
      body: JSON.stringify({ line_id: lineId }),
    }),

  detectAnomalies: (grid: number[][], thresholdSigma = 2.0, direction = "both", pixelSizeM = 1.0) =>
    request<AnomalyDetectionResult>("/api/v1/analysis/anomaly-detection", {
      method: "POST",
      body: JSON.stringify({ grid, threshold_sigma: thresholdSigma, direction, pixel_size_m: pixelSizeM }),
    }),

  sendChatMessage: (surveyId: string, message: string) =>
    request<ChatResponse>(`/api/v1/surveys/${surveyId}/chat`, { method: "POST", body: JSON.stringify({ message }) }),

  chatHistory: (surveyId: string) =>
    request<Array<{ role: string; content: string; created_at: string }>>(`/api/v1/surveys/${surveyId}/chat/history`),
};
