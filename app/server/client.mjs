/** Dependency-free browser/Node transport. Credentials and retry intents stay in memory. */
export function newId() {
  return Array.from(crypto.getRandomValues(new Uint8Array(16)), b => b.toString(16).padStart(2, "0")).join("");
}
export function newToken() {
  return Array.from(crypto.getRandomValues(new Uint8Array(32)), b => b.toString(16).padStart(2, "0")).join("");
}
export class RequestError extends Error {
  constructor(code, outcome = "not_sent") {
    super({timeout:"Request timed out; reconcile before starting another write.", aborted:"Request cancelled; cancellation does not undo a server write.", network_error:"Connection failed; the server outcome may be unknown.", invalid_response:"The server response could not be read.", client_inactive:"This client no longer has usable credentials."}[code] || "Request could not be completed.");
    this.name = "RequestError";
    this.code = code;
    this.outcome = outcome;
  }
}
export class ApiError extends Error {
  constructor(status, error, outcome = "response_received") {
    super(error?.message || "API request failed");
    this.name = "ApiError";
    this.status = status;
    this.code = error?.code || "request_failed";
    this.details = error?.details || {};
    this.outcome = outcome;
  }
}
function serialise(value) {
  try {
    return JSON.stringify(value, (_key, item) => {
      if (typeof item === "number" && !Number.isFinite(item)) throw new TypeError();
      if (["bigint", "function", "symbol"].includes(typeof item)) throw new TypeError();
      return item;
    });
  } catch { throw new TypeError("Request data must be finite, serialisable JSON."); }
}
function deadline(value) {
  if (!Number.isInteger(value) || value < 1 || value > 120000) throw new TypeError("timeoutMs must be an integer from 1 to 120000.");
  return value;
}
export class GenAIClient {
  #base; #token; #sid; #fetch; #timeout; #state = "active";
  #scope = newId(); #intents = new WeakSet(); #listeners = new Set(); #requests = new Set(); #urls = new Set();
  constructor({baseUrl = "http://127.0.0.1:3000", sessionId, token, allowLan = false, timeoutMs = 10000, fetchImpl = (...args) => fetch(...args)}) {
    const url = new URL(baseUrl);
    if (!["http:", "https:"].includes(url.protocol) || (!allowLan && !["localhost", "127.0.0.1"].includes(url.hostname)) || url.username || url.password || url.search || url.hash || url.pathname !== "/") {
      throw new TypeError("Use an HTTP(S) origin; network hosts require explicit allowLan.");
    }
    this.#base = url.origin; this.#sid = sessionId; this.#token = token;
    this.#timeout = deadline(timeoutMs); this.#fetch = fetchImpl;
  }
  get state() { return this.#state; }
  onState(listener) {
    if (typeof listener !== "function") throw new TypeError("A state listener must be a function.");
    this.#listeners.add(listener);
    return () => this.#listeners.delete(listener);
  }
  #active() { if (this.#state !== "active") throw new RequestError("client_inactive"); }
  #end(state, current) {
    if (this.#state !== "active") return;
    this.#state = state;
    this.#token = undefined;
    for (const request of this.#requests) if (request !== current) request.cancel("client_inactive");
    for (const url of this.#urls) URL.revokeObjectURL(url);
    this.#urls.clear();
    for (const listener of this.#listeners) { try { listener(state); } catch { /* Observers cannot break cleanup. */ } }
    this.#listeners.clear();
  }
  dispose() { this.#end("disposed"); }
  createMediaUrl(blob) {
    this.#active();
    if (this.#urls.size >= 16) throw new RangeError("Release a media URL before opening another.");
    const url = URL.createObjectURL(blob); this.#urls.add(url); return url;
  }
  revokeMediaUrl(url) { if (this.#urls.delete(url)) URL.revokeObjectURL(url); }
  async #request(method, path, body, requestId, format = "json", options = {}, {auth = true, readOnly = method === "GET", ready = false, deleted = false} = {}) {
    this.#active();
    const timeoutMs = deadline(options.timeoutMs ?? this.#timeout);
    const signal = options.signal;
    if (signal?.aborted) throw new RequestError("aborted");
    const controller = new AbortController();
    let sent = false, received = false, cancelReject;
    const outcome = () => sent && (!readOnly || !received) ? "unknown" : sent ? "response_received" : "not_sent";
    const cancelled = new Promise((_resolve, reject) => { cancelReject = reject; });
    const request = {cancel: code => { cancelReject(new RequestError(code, outcome())); controller.abort(); }};
    const abort = () => request.cancel("aborted");
    signal?.addEventListener("abort", abort, {once:true});
    const timer = setTimeout(() => request.cancel("timeout"), timeoutMs);
    this.#requests.add(request);
    const run = async () => {
      const headers = {};
      if (auth) headers.Authorization = `Bearer ${this.#token}`;
      if (body !== undefined) headers["Content-Type"] = "application/json";
      if (requestId) headers["X-Request-ID"] = requestId;
      let response;
      try {
        sent = true;
        response = await this.#fetch(this.#base + path, {method, headers, body, signal:controller.signal, cache:"no-store", credentials:"omit", redirect:"error"});
      } catch { throw new RequestError("network_error", outcome()); }
      received = true;
      if (controller.signal.aborted) throw new RequestError("aborted", outcome());
      this.#active();
      let payload;
      // Authoritative loss of authority must invalidate the client even if its error body stalls.
      if (auth && response.status === 401) this.#end("revoked", request);
      try {
        payload = !response.ok || format === "json" ? await response.json() : format === "blob" ? await response.blob() : await response.text();
      } catch { throw new RequestError("invalid_response", outcome()); }
      if (controller.signal.aborted) throw new RequestError("aborted", outcome());
      if (!response.ok && !(ready && response.status === 503)) {
        if (auth && response.status === 410 && ["session_expired", "session_deleted"].includes(payload?.error?.code)) {
          this.#end(payload.error.code === "session_expired" ? "expired" : "deleted", request);
        }
        throw new ApiError(response.status, payload?.error, !readOnly && (response.status >= 500 || payload?.error?.code === "control_replay_expired") ? "unknown" : "response_received");
      }
      this.#active();
      if (deleted || (method === "GET" && path === this.#path && payload?.state === "deleted" && payload?.content_available === false && payload?.session_id === this.#sid)) this.#end("deleted", request);
      return payload;
    };
    try { return await Promise.race([run(), cancelled]); }
    finally { clearTimeout(timer); signal?.removeEventListener("abort", abort); this.#requests.delete(request); }
  }
  get #path() { return `/api/sessions/${encodeURIComponent(this.#sid)}`; }
  create({ownerName, title, retentionSeconds = 86400, timezone}, options) {
    this.#active();
    return this.#request("POST", "/api/sessions", serialise({session_id:this.#sid, owner_token:this.#token, owner_name:ownerName, title, retention_seconds:retentionSeconds, ...(timezone ? {timezone} : {})}), undefined, "json", options, {auth:false});
  }
  join({invitation, name, policyVersion}, options) {
    this.#active();
    return this.#request("POST", this.#path + "/join", serialise({invitation, token:this.#token, name, policy_version:policyVersion}), undefined, "json", options, {auth:false});
  }
  /** Retain and explicitly retry this SAME object after an uncertain write. Never rebase it silently. */
  intent(operation, payload = {}, {controlSequence} = {}) {
    this.#active();
    if (typeof operation !== "string" || !operation || !payload || typeof payload !== "object" || Array.isArray(payload)) throw new TypeError("A command needs an operation and payload object.");
    if (controlSequence !== undefined && (!Number.isSafeInteger(controlSequence) || controlSequence < 0)) throw new TypeError("A control sequence must be a non-negative safe integer.");
    const intent = Object.freeze({requestId:newId(), serialized:serialise({operation, payload, control_sequence:controlSequence}), sessionId:this.#sid, origin:this.#base, clientScope:this.#scope});
    this.#intents.add(intent); return intent;
  }
  submit(intent, options) {
    if (!this.#intents.has(intent)) throw new TypeError("Submit the original intent created by this client.");
    return this.#request("POST", this.#path + "/commands", intent.serialized, intent.requestId, "json", options);
  }
  wakewordStart(options) { return this.#request("POST", this.#path + "/wakeword/start", "{}", undefined, "json", options); }
  wakewordBatch(streamId, sequence, base64, options) {
    return this.#request("POST", this.#path + "/wakeword/batch", serialise({stream_id:streamId, sequence, base64}), undefined, "json", options);
  }
  wakewordStop(streamId, options) {
    return this.#request("POST", this.#path + "/wakeword/stop", serialise({stream_id:streamId}), undefined, "json", options);
  }
  snapshot(options) { return this.#request("GET", this.#path, undefined, undefined, "json", options); }
  delta(sinceSeq, options) { return this.#request("GET", this.#path + `?since_seq=${encodeURIComponent(sinceSeq)}`, undefined, undefined, "json", options); }
  events(after = 0, options) { return this.#request("GET", this.#path + `/events?after=${encodeURIComponent(after)}`, undefined, undefined, "json", options); }
  record(id, revision, options) {
    const query = revision === undefined ? "" : `?revision=${encodeURIComponent(revision)}`;
    return this.#request("GET", this.#path + `/records/${encodeURIComponent(id)}` + query, undefined, undefined, "json", options);
  }
  media(id, options) { return this.#request("GET", this.#path + `/sources/${encodeURIComponent(id)}/media`, undefined, undefined, "blob", options); }
  crop(id, revision, regionId, options) { return this.#request("GET", this.#path + `/sources/${encodeURIComponent(id)}/regions/${encodeURIComponent(regionId)}?revision=${encodeURIComponent(revision)}`, undefined, undefined, "blob", options); }
  exportSnapshot(includeUnresolved, options) { return this.#request("POST", this.#path + "/export-snapshot", serialise({include_unresolved:includeUnresolved}), undefined, "json", options, {readOnly:true}); }
  export(id, format = "json", options) {
    if (!["json", "markdown"].includes(format)) throw new TypeError("Choose json or markdown");
    return this.#request("GET", this.#path + `/exports/${encodeURIComponent(id)}?format=${format}`, undefined, undefined, format === "markdown" ? "text" : "json", options);
  }
  readiness(options) { return this.#request("GET", "/ready", undefined, undefined, "json", options, {auth:false, readOnly:true, ready:true}); }
  diagnostics(options) { return this.#request("GET", this.#path + "/diagnostics", undefined, undefined, "json", options); }
  delete(options) { return this.#request("DELETE", this.#path, undefined, undefined, "json", options, {deleted:true}); }
}
