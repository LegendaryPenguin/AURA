import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import qrcode from "qrcode-terminal";

const HOST = "0.0.0.0";
const ANSI_REGEX = /\u001b\[[0-9;]*m/g;

let viteProcess = null;
let tunnelProcess = null;
let resolvedPort = null;
let tunnelStarted = false;
const streamBuffers = new WeakMap();

async function startTunnelForPort(port) {
  if (tunnelStarted) {
    return;
  }
  tunnelStarted = true;
  process.stdout.write(`[dev-tunnel] Opening Cloudflare tunnel for localhost:${port}...\n`);
  let command = process.platform === "win32" ? "cloudflared.exe" : "cloudflared";
  if (process.platform === "win32" && !existsSync(command)) {
    const x86Path = "C:\\Program Files (x86)\\cloudflared\\cloudflared.exe";
    const x64Path = "C:\\Program Files\\cloudflared\\cloudflared.exe";
    if (existsSync(x86Path)) {
      command = x86Path;
    } else if (existsSync(x64Path)) {
      command = x64Path;
    }
  }
  tunnelProcess = spawn(command, ["tunnel", "--url", `http://127.0.0.1:${port}`], {
    stdio: ["ignore", "pipe", "pipe"],
    shell: false,
  });

  const onTunnelData = (chunk) => {
    const text = String(chunk).replace(ANSI_REGEX, "");
    const urlMatches = text.match(/https:\/\/[a-zA-Z0-9-]+\.trycloudflare\.com/g) ?? [];
    const tunnelUrl =
      urlMatches.find((candidate) => candidate !== "https://api.trycloudflare.com") ?? null;
    const urlMatch = tunnelUrl ? [tunnelUrl] : null;
    if (urlMatch) {
      const url = urlMatch[0];
      process.stdout.write(`\n[dev-tunnel] Public URL: ${url}\n`);
      process.stdout.write("[dev-tunnel] Scan this QR code on your phone:\n\n");
      qrcode.generate(url, { small: true });
      process.stdout.write("\n[dev-tunnel] Keep this terminal open. Press Ctrl+C to stop.\n");
      return;
    }
    process.stdout.write(`[cloudflared] ${text}`);
  };

  tunnelProcess.stdout.on("data", onTunnelData);
  tunnelProcess.stderr.on("data", onTunnelData);

  tunnelProcess.on("exit", (code) => {
    if (code !== 0) {
      process.stderr.write(`[dev-tunnel] cloudflared exited with code ${code}\n`);
    } else {
      process.stdout.write("[dev-tunnel] Tunnel closed.\n");
    }
  });
}

function maybeCapturePortAndTunnel(text) {
  const clean = text.replace(ANSI_REGEX, "");
  const match = clean.match(/Local:\s+https?:\/\/localhost:(\d+)(?:\/|\b)/);
  if (!match) {
    return;
  }
  resolvedPort = Number(match[1]);
  if (Number.isNaN(resolvedPort)) {
    return;
  }
  void startTunnelForPort(resolvedPort);
}

function processChunkLines(stream, chunkText) {
  const previous = streamBuffers.get(stream) ?? "";
  const combined = previous + chunkText;
  const lines = combined.split(/\r?\n/);
  const trailing = lines.pop() ?? "";
  streamBuffers.set(stream, trailing);

  for (const line of lines) {
    if (line.includes("Local:")) {
      process.stdout.write("\n[dev-tunnel] Local app is up.\n");
    }
    maybeCapturePortAndTunnel(line);
  }
}

function forwardOutput(stream) {
  stream.on("data", (chunk) => {
    process.stdout.write(chunk);
    processChunkLines(stream, chunk.toString());
  });
}

function cleanupAndExit(code = 0) {
  if (tunnelProcess && !tunnelProcess.killed) {
    tunnelProcess.kill("SIGINT");
  }
  if (viteProcess && !viteProcess.killed) {
    viteProcess.kill("SIGINT");
  }
  process.exit(code);
}

async function main() {
  process.stdout.write("[dev-tunnel] Starting Vite dev server...\n");
  const command = process.platform === "win32" ? `npm run dev -- --host ${HOST}` : `npm run dev -- --host ${HOST}`;
  viteProcess = spawn(command, {
    stdio: ["inherit", "pipe", "pipe"],
    shell: true,
  });

  forwardOutput(viteProcess.stdout);
  forwardOutput(viteProcess.stderr);

  viteProcess.on("exit", (code) => {
    if (code !== 0) {
      process.stderr.write(`[dev-tunnel] Vite exited with code ${code}\n`);
      cleanupAndExit(code ?? 1);
    }
  });

  const timeout = setTimeout(() => {
    if (!tunnelStarted) {
      process.stderr.write("[dev-tunnel] Timed out waiting for Vite local URL output.\n");
      cleanupAndExit(1);
    }
  }, 45000);

  const interval = setInterval(() => {
    if (tunnelStarted) {
      clearInterval(interval);
      clearTimeout(timeout);
    }
  }, 200);
}

process.on("SIGINT", () => cleanupAndExit(0));
process.on("SIGTERM", () => cleanupAndExit(0));

main().catch((error) => {
  process.stderr.write(`[dev-tunnel] ${error instanceof Error ? error.message : String(error)}\n`);
  cleanupAndExit(1);
});

