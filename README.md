# 🔥 AURA
Augmented Reality Understanding Assistant.

![AURA Architecture](./docs/assets/aura_system_architecture_infographic.png)

AURA turns your phone camera into a spatial action layer for the physical world.

Instead of giving users another chatbot or static camera app, AURA projects useful information directly onto the scene in front of them. It highlights what matters, explains why it matters, and guides the next step through augmented overlays for care, sustainability, and wayfinding scenarios.

Built for LA Hacks, the project combines mobile AR-style interaction, edge AI architecture, spatial UI, and agentic workflows to make real-world environments feel interactive, understandable, and actionable.

## ✨ Inspiration

We wanted to make spatial AI feel like something people could actually see and use instead of just another chatbot or camera app.

A lot of AI tools explain the world through text, but in real life people do not always need a paragraph. They need to know what matters in the scene in front of them. We were inspired by AR and VR experiences where digital information feels attached to the physical world, and by the idea that a phone camera could become more than a lens.

That led us to AURA: an augmented reality understanding assistant that turns everyday environments into interactive spatial guidance.

## 📱 What It Does

AURA transforms a phone camera snapshot into an augmented action layer.

Users can point their phone at everyday environments and see animated overlays that highlight:

care risks
sustainability actions
wayfinding routes
important objects
recommendations
next steps

We focused on three example use cases to show the range of what AURA can support.

### 1. Care Safety Scan

AURA can highlight medication safety cues such as:

pill bottles
pill organizers
water bottles
phones
written instructions

The goal is to help users and caregivers notice important health-related context directly in the scene.

### 2. Sustainability Audit

AURA can point out energy use and waste sorting opportunities such as:

idle chargers
food containers
plastic cups
lamps
recycling bins

The goal is to turn a normal room into an instant sustainability checklist.

### 3. Wayfinding Assistant

AURA can draw route guidance through a physical space while warning about obstacles.

It can highlight:

open paths
exit doors
obstacles
landmarks
safe route directions

The goal is to make navigation more visual, accessible, and spatial.

## 🧱 How We Built It

We built AURA as a mobile-first spatial intelligence experience.

The project is split into several major layers:

### 1. Client Experience Layer

This handles the mobile-facing user experience:

phone camera capture
scenario selection
image capture
spatial overlay rendering
animated HUD elements
route guidance
result screens

The user chooses an experience, captures a scene, and sees AURA render an augmented result view directly on top of the captured image.

### 2. Application Control Plane

This handles the structure of the ideal backend system:

FastAPI gateway
health checks
scene requests
streaming sessions
concurrency control
overlay composition
WebSocket overlay updates

The control plane is designed to coordinate requests between the frontend, model servers, and agent workflows.

### 3. ASUS Edge Inference Plane

The ideal version of AURA is designed around an ASUS edge supercomputer runtime.

This layer includes:

vLLM for serving Qwen2.5-VL
SAM2 for object segmentation and tracking
depth estimation for spatial mapping
Whisper for voice input
local model caching
GPU job routing

The goal is to keep inference local, low-latency, and privacy-preserving.

### 4. Agent and Workflow Layer

AURA is also designed to connect spatial understanding to action.

Structured scene context can be passed into agent workflows, such as:

CareAgent
EcoAgent
NavigationAgent
EdgeRuntimeAgent

These agents turn scene understanding into recommendations, checklists, handoffs, and next steps.

## 🛠️ Tech Stack

We built AURA with:

React
TypeScript
Vite
CSS
Browser Camera APIs
FastAPI
Python
WebSockets
vLLM
Qwen2.5-VL
SAM2
Depth Anything
Whisper
Fetch.ai
Agentverse
ASUS Ascent GX10

We chose this stack because AURA needed to support both:

a polished mobile AR-style interface
a serious local edge-AI architecture

while still being fast enough to build and iterate on during a hackathon.

## 🧠 Architecture

AURA is designed as a spatial AI pipeline.

At a high level:

phone camera input
goes into the application control plane
which routes the scene to local model servers
which produce detections, masks, depth, and reasoning
which are composed into overlays
which return to the phone as an augmented interface

The ideal architecture includes:

### Client Experience

Mobile Web App
Web Dashboard
Camera, Mic, and Sensor Capture
Overlay HUD and Wayfinding
Simulate
Inform
Guide
Monitor

### Application Control Plane

FastAPI Gateway
Session Manager
Auth and Policy
Scenario Orchestrator
Continuous Scan Controller
Concurrency Guard
Rate Limiter
Overlay Composer
Results Aggregator
WebSocket Push Service
Background Task Queue

### ASUS Supercomputer Inference Plane

ASUS GX10 Edge Runtime
Qwen2.5-VL through vLLM
SAM2 Segmentation and Tracking
Depth Mapping
Whisper ASR
Snapshot Pipeline
Model Cache
GPU Scheduler

### Agent and Workflow Layer

Fetch.ai Agent Router
AuraSpatialActionAgent
CareAgent
EcoAgent
NavigationAgent
EdgeRuntimeAgent
Workflow Rules Engine

## 🚧 Challenges We Ran Into

One of our biggest challenges was balancing ambition with reliability.

The original vision involved live local model inference, real-time segmentation, depth mapping, and agentic workflows running through a supercomputer-backed architecture. That was exciting, but it also introduced a lot of environment, startup, GPU, and model-serving complexity.

We had to think carefully about how to still communicate the full product vision through a focused and polished experience.

Another challenge was making spatial overlays feel meaningful. We did not want to just show boxes on a picture. We had to design the flow so the phone camera, capture step, animated scan, overlay timing, route drawing, severity labels, and action panels all worked together to create the feeling of spatial intelligence.

The hardest design problem was making the experience feel like AURA was augmenting the real world, not just decorating an image.

## 🏆 Accomplishments That We're Proud Of

We are proud that AURA feels like a real product experience instead of just a technical prototype.

The demo turns phone camera captures into polished augmented scenes with:

visual guidance
action summaries
spatial overlays
route animations
HUD-style scan effects
real-world use cases

We are also proud that the three example use cases cover very different kinds of real-world value:

care safety
sustainability
wayfinding

We are especially proud of the visual direction. The animated overlays, scanning effects, route guidance, and HUD-style interface make the project feel futuristic while still being understandable.

We are also proud that we preserved the bigger architecture vision. AURA is designed around a broader model-backed pipeline where the same interface can be powered by local inference, segmentation, depth, and agents.

## 📚 What We Learned

### Farrell

I learned how important it is to design for the demo experience, not just the technical architecture. At first, we were focused on getting the full model-serving pipeline working, but I learned that a hackathon project also needs a reliable story that judges can understand immediately. Building AURA made me think much more carefully about how to turn AI outputs into a visual interface that actually helps people in the moment.

### Nischay

I learned how to structure a mobile-first camera experience in a way that feels natural on a phone. This meant thinking about the full flow from choosing an experience, opening the camera, aligning the scene, capturing the image, and transitioning into the augmented result view.

We also learned how to design overlay systems using normalized coordinates and spatial UI patterns. Instead of placing elements randomly, we had to think about how boxes, labels, confidence values, route arrows, and action panels should appear in relation to the scene.

Most importantly, we learned how to think about project architecture beyond the immediate interface. The ideal version of AURA includes a control plane, local inference servers, model caches, segmentation, depth mapping, streaming overlays, and agent handoffs.

## 🚀 Setup

## 🚀 Setup Instructions

Follow these steps to run AURA locally.

### 1. Clone the repository

```bash
git clone <your-repo-url>
2. Move into the project folder
cd <your-project-folder>
3. Open the project in your code editor

For example, in VS Code:

code .
4. Move into the client folder
cd client
5. Install dependencies using the project lockfile

This project includes a package-lock.json, so install dependencies with:

npm ci

Using npm ci ensures the exact dependency versions defined in our lockfile are installed, which makes setup more consistent across machines.

6. Add the demo scene images

Place the three demo images in:

client/public/demo-scenes/medical1.png
client/public/demo-scenes/sustainability2.png
client/public/demo-scenes/wayfinding3.png
7. Start the development server
npm run dev -- --host 0.0.0.0
8. Open the app in your browser

After the dev server starts, open the local URL shown in your terminal, usually:

http://localhost:5173
