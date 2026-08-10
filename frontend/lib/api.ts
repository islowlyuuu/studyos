export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

/** 解析 SSE 文本流，逐个回调 JSON 事件。 */
export async function readSSE(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  onEvent: (data: any) => void,
) {
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      const line = frame.trim();
      if (line.startsWith("data:")) {
        onEvent(JSON.parse(line.slice(5).trim()));
      }
    }
  }
}
