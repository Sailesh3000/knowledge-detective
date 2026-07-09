const BASE_URL = "http://localhost:8000";

export interface Citation {
  id: string;
  title: string;
  source: string;
  author: string;
  timestamp: string;
  url?: string;
}

export interface ChunkUsed {
  chunk_id: string;
  document_id: string;
  title: string;
  content: string;
  author: string;
  source: string;
  timestamp: string;
  url?: string;
  score?: number;
}

export interface QueryResponse {
  question: string;
  plan: {
    sub_queries: string[];
    search_type: string;
    entities: string[];
    topics: string[];
  };
  answer: string;
  citations: Citation[];
  chunks_used: ChunkUsed[];
  elapsed_seconds: number;
}

export interface TimelineEvent {
  id: string;
  title: string;
  source: string;
  timestamp: string;
  author: string;
  snippet: string;
}

export interface TimelineResponse {
  topic: string | null;
  events: TimelineEvent[];
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  properties?: Record<string, any>;
  x?: number;
  y?: number;
}

export interface GraphLink {
  source: string;
  target: string;
  type: string;
}

export interface GraphResponse {
  nodes: GraphNode[];
  links: GraphLink[];
}

export async function askQuestion(question: string): Promise<QueryResponse> {
  const response = await fetch(`${BASE_URL}/api/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question }),
  });
  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchTimeline(topic?: string): Promise<TimelineResponse> {
  const url = topic
    ? `${BASE_URL}/api/timeline?topic=${encodeURIComponent(topic)}`
    : `${BASE_URL}/api/timeline`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchGraph(entity?: string): Promise<GraphResponse> {
  const url = entity
    ? `${BASE_URL}/api/graph?entity=${encodeURIComponent(entity)}`
    : `${BASE_URL}/api/graph`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }
  return response.json();
}
