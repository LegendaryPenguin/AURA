from datetime import datetime, timezone
from uuid import uuid4
import re

from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
    chat_protocol_spec,
)

# -----------------------
# Basic config
# -----------------------

# NEW AGENT IDENTITY
# This creates a fresh agent address and avoids the stale mailbox credentials
# from the old manual-demo-agent identity.
AGENT_NAME = "AURA-spatial-demo-agent"
AGENT_SEED = "aura brand new spatial demo agent fresh mailbox seed 2026 hackathon"
AGENT_PORT = 8001

agent = Agent(
    name=AGENT_NAME,
    seed=AGENT_SEED,
    port=AGENT_PORT,
    mailbox=True,
    publish_agent_details=True,
)

# -----------------------
# Agentverse Chat Protocol
# -----------------------

protocol = Protocol(spec=chat_protocol_spec)

IMAGE_URL = "https://YOUR_PUBLIC_IMAGE_LINK_HERE.png"
SILENCE_ON_UNKNOWN = False


# -----------------------
# Demo scenario memory
# -----------------------

SCENE_MEMORY = {
    "initial": "At first, the scene had a table with chairs around it, and nothing was on the table.",
    "later": "Later, the chairs had moved, and a black water bottle appeared on top of the table.",
    "main_change": "The chairs moved, and a black water bottle appeared on the table.",
}


# -----------------------
# Demo prompt list
# -----------------------

DEMO_PROMPTS = [
    "What changed?",
    "What moved?",
    "What is on the table now?",
    "Was the table empty before?",
    "Did someone move the chairs?",
    "Can you simulate what happened?",
    "How do I restore the scene?",
    "Show me the comparison.",
    "What tools do you have?",
]


# -----------------------
# AURA internal tool modes
# -----------------------

CUSTOM_CASES = [
    {
        "name": "hello_intro",
        "mode": "Intro",
        "tool_name": None,
        "tool_call": None,
        "tool_result": None,
        "triggers": ["hi", "hello", "hey", "yo", "sup"],
        "responses": [
            "Hi, I’m AURA — your spatial memory assistant.",
            "For this demo, I remember a simple scene: first there was a table with chairs around it, and the table was empty. Later, the chairs moved and a black water bottle appeared on the table.",
            "I have four internal tools for demo purposes: AURA_Monitor detects changes, AURA_Simulate explains what may have happened, AURA_Inform gives clean facts, and AURA_Guide tells you what to do next.",
            "For demo purposes, ask me about:",
            "\n".join([f"- {prompt}" for prompt in DEMO_PROMPTS]),
        ],
    },
    {
        "name": "monitor_changed",
        "mode": "Monitor",
        "tool_name": "AURA_Monitor",
        "tool_call": 'AURA_Monitor.detect_scene_changes(scene="table_and_chairs_demo")',
        "tool_result": "Detected changed chair positions and one new object on the table.",
        "triggers": [
            "changed",
            "changedd",
            "change",
            "different",
            "difference",
            "compare",
            "what changed",
            "did anything change",
            "something changed",
            "scene changed",
            "room changed",
            "table changed",
            "chairs changed",
        ],
        "responses": [
            "[Monitor Mode] I detected two main changes in the scene.",
            "First, the chairs are no longer in their original positions around the table. Second, a black water bottle appeared on the table even though the table was empty before.",
            f"Spatial memory comparison view: {IMAGE_URL}",
        ],
    },
    {
        "name": "monitor_chairs",
        "mode": "Monitor",
        "tool_name": "AURA_Monitor",
        "tool_call": 'AURA_Monitor.track_object_motion(objects=["chairs"])',
        "tool_result": "The chairs changed position between the initial scene and the later scene.",
        "triggers": [
            "chair",
            "chairs",
            "seat",
            "seats",
            "seating",
            "moved chair",
            "moved chairs",
            "what moved",
            "objects moved",
        ],
        "responses": [
            "[Monitor Mode] The chairs are the main moved objects.",
            "In the original memory, the chairs were arranged around the table. In the later scene, their positions changed, so I marked the seating area as disturbed.",
        ],
    },
    {
        "name": "inform_bottle",
        "mode": "Inform",
        "tool_name": "AURA_Inform",
        "tool_call": 'AURA_Inform.inspect_object(object="black water bottle")',
        "tool_result": "The black water bottle is a new object that appears only in the later scene.",
        "triggers": [
            "bottle",
            "water bottle",
            "black bottle",
            "black water bottle",
            "object",
            "new object",
            "new thing",
            "appeared",
            "what appeared",
        ],
        "responses": [
            "[Inform Mode] The new object is a black water bottle.",
            "It was not present in the first scene. It appears only in the later scene, sitting on top of the table.",
        ],
    },
    {
        "name": "inform_table",
        "mode": "Inform",
        "tool_name": "AURA_Inform",
        "tool_call": 'AURA_Inform.describe_surface_state(surface="table")',
        "tool_result": "The table was empty before. Later, it had a black water bottle on top.",
        "triggers": [
            "table",
            "empty",
            "empty table",
            "on the table",
            "what is on the table",
            "was the table empty",
            "what was there before",
            "what was on it",
        ],
        "responses": [
            "[Inform Mode] The table started empty.",
            "In the later scene, the table is no longer empty because a black water bottle is now on top of it.",
        ],
    },
    {
        "name": "simulate_what_happened",
        "mode": "Simulate",
        "tool_name": "AURA_Simulate",
        "tool_call": 'AURA_Simulate.replay_scene_transition(before="empty_table", after="moved_chairs_with_bottle")',
        "tool_result": "Most likely transition: chairs moved first, then the black water bottle was placed on the table.",
        "triggers": [
            "simulate",
            "simulation",
            "replay",
            "what happened",
            "how did it happen",
            "could have happened",
            "maybe happened",
            "scenario",
        ],
        "responses": [
            "[Simulate Mode] A likely sequence is: the scene began with an empty table and chairs in place.",
            "Then someone or something moved the chairs. After that, a black water bottle was placed on the table.",
            "I cannot prove who did it, but that sequence best explains the before-and-after spatial memory.",
        ],
    },
    {
        "name": "guide_restore",
        "mode": "Guide",
        "tool_name": "AURA_Guide",
        "tool_call": 'AURA_Guide.generate_restore_steps(target_state="original_empty_table_and_chairs")',
        "tool_result": "Restore by removing the bottle and returning the chairs to their remembered positions.",
        "triggers": [
            "restore",
            "fix",
            "reset",
            "put it back",
            "return",
            "return to normal",
            "original setup",
            "undo",
            "revert",
            "how do i fix",
            "how do i restore",
        ],
        "responses": [
            "[Guide Mode] To restore the original scene, do two things.",
            "First, remove the black water bottle from the table. Second, move the chairs back to their original positions around the table.",
            "After that, the scene should match the remembered version: table empty, chairs arranged normally.",
        ],
    },
    {
        "name": "person_or_intruder",
        "mode": "Monitor",
        "tool_name": "AURA_Monitor",
        "tool_call": 'AURA_Monitor.check_presence_evidence(changes=["moved_chairs", "new_bottle"])',
        "tool_result": "The scene changed, but there is not enough evidence to identify who caused it.",
        "triggers": [
            "someone",
            "person",
            "people",
            "intruder",
            "visitor",
            "who moved",
            "who touched",
            "did someone",
            "was someone there",
            "did someone touch it",
        ],
        "responses": [
            "[Monitor Mode] I cannot identify a person from this memory alone.",
            "What I can say is that the scene changed: the chairs moved and a black water bottle appeared on the table.",
            "That is consistent with someone interacting with the space, but I cannot prove who it was.",
        ],
    },
    {
        "name": "show_image",
        "mode": "Guide",
        "tool_name": "AURA_Guide",
        "tool_call": 'AURA_Guide.open_comparison_view(scene="table_and_chairs_demo")',
        "tool_result": "Comparison view prepared.",
        "triggers": [
            "image",
            "picture",
            "photo",
            "show image",
            "show picture",
            "send image",
            "show comparison",
            "visualize",
        ],
        "responses": [
            "[Guide Mode] Here is the visual comparison for the scene.",
            f"Spatial memory comparison view: {IMAGE_URL}",
        ],
    },
    {
        "name": "explain_aura",
        "mode": "Intro",
        "tool_name": "AURA_Inform",
        "tool_call": 'AURA_Inform.explain_available_tools()',
        "tool_result": "AURA has four demo tools: Monitor, Simulate, Inform, and Guide.",
        "triggers": [
            "what are you",
            "who are you",
            "what is aura",
            "explain aura",
            "how do you work",
            "what can you do",
            "modes",
            "mode",
            "tools",
            "tool",
            "subagents",
            "subagent",
        ],
        "responses": [
            "I’m AURA, a spatial memory assistant.",
            "In this demo, I remember a before-and-after scene: an empty table with chairs first, then moved chairs and a black water bottle on the table later.",
            "My internal demo tools are:",
            "- AURA_Monitor: detects what changed.",
            "- AURA_Simulate: explains what may have happened.",
            "- AURA_Inform: gives direct facts about the scene.",
            "- AURA_Guide: tells you how to inspect or restore the space.",
        ],
    },
]


# -----------------------
# Core helpers
# -----------------------

def now():
    return datetime.now(timezone.utc)


def extract_text(msg: ChatMessage) -> str:
    parts = []

    for item in msg.content:
        if isinstance(item, TextContent):
            parts.append(item.text)

    text = " ".join(parts).strip()
    text = text.replace(f"@{agent.address}", "").strip()

    return text


def trigger_matches(user_text: str, trigger: str) -> bool:
    lowered = user_text.lower()
    trigger = trigger.lower().strip()

    if len(trigger) <= 3:
        pattern = r"\b" + re.escape(trigger) + r"\b"
        return re.search(pattern, lowered) is not None

    return trigger in lowered


def find_case(user_text: str):
    for case in CUSTOM_CASES:
        for trigger in case["triggers"]:
            if trigger_matches(user_text, trigger):
                return case

    return None


def format_fake_tool_call(case: dict) -> list[str]:
    tool_name = case.get("tool_name")
    tool_call = case.get("tool_call")
    tool_result = case.get("tool_result")

    if not tool_name or not tool_call:
        return []

    return [
        f"Calling tool: {tool_name}",
        f"`{tool_call}`",
        f"Tool result: {tool_result}",
    ]


def get_fallback_response():
    return [
        "Calling tool: AURA_Inform",
        '`AURA_Inform.retrieve_demo_context(scene="table_and_chairs_demo")`',
        "Tool result: Retrieved the active demo memory.",
        "I’m AURA. I may not have matched that exact wording, but I’m still using the same demo memory.",
        "The remembered scene started with an empty table and chairs around it. Later, the chairs moved and a black water bottle appeared on the table.",
        "Try asking: “what changed?”, “what moved?”, “what is on the table?”, “simulate what happened”, or “how do I restore it?”",
    ]


async def send_responses(ctx: Context, recipient: str, responses: list[str]):
    clean_responses = []

    for response in responses:
        if response and response.strip():
            clean_responses.append(response.strip())

    if not clean_responses:
        return

    full_text = "\n\n".join(clean_responses)

    await ctx.send(
        recipient,
        ChatMessage(
            timestamp=now(),
            msg_id=uuid4(),
            content=[
                TextContent(type="text", text=full_text),
                EndSessionContent(type="end-session"),
            ],
        ),
    )


# -----------------------
# Chat Protocol handlers
# -----------------------

@protocol.on_message(ChatMessage)
async def handle_message(ctx: Context, sender: str, msg: ChatMessage):
    print("\n" + "=" * 70)
    print("RAW CHAT MESSAGE RECEIVED")
    print(f"FROM: {sender}")
    print(f"MSG ID: {msg.msg_id}")
    print(f"RAW CONTENT: {msg.content}")
    print("=" * 70)

    await ctx.send(
        sender,
        ChatAcknowledgement(
            timestamp=now(),
            acknowledged_msg_id=msg.msg_id,
        ),
    )

    incoming_text = extract_text(msg)

    print("\n" + "=" * 70)
    print("NEW AURA MESSAGE")
    print(f"FROM: {sender}")
    print(f"TEXT: {incoming_text}")
    print("=" * 70)

    if not incoming_text:
        await send_responses(
            ctx,
            sender,
            [
                "I received your message, but I could not extract readable text from it.",
                "Try sending: hi",
            ],
        )
        return

    matched_case = find_case(incoming_text)

    if matched_case is None:
        print("No exact keyword matched.")

        if SILENCE_ON_UNKNOWN:
            print("Silence mode enabled: sending no reply.")
            return

        await send_responses(ctx, sender, get_fallback_response())
        return

    print(f"Matched case: {matched_case['name']}")
    print(f"Mode: {matched_case['mode']}")

    tool_lines = format_fake_tool_call(matched_case)
    final_responses = tool_lines + matched_case["responses"]

    await send_responses(ctx, sender, final_responses)
    print("AURA sent scripted response.")


@protocol.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    ctx.logger.info(f"Message acknowledged by {sender}: {msg.acknowledged_msg_id}")


@agent.on_event("startup")
async def startup(ctx: Context):
    inspector_link = (
        f"https://agentverse.ai/inspect/?uri=http%3A//127.0.0.1%3A{AGENT_PORT}"
        f"&address={agent.address}"
    )

    print()
    print("AURA fresh single-agent demo is running.")
    print(f"Agent display name: {AGENT_NAME}")
    print(f"Agent address: {agent.address}")
    print(f"Port: {AGENT_PORT}")
    print()
    print("Fetch.ai / Agentverse:")
    print("  Agentverse-compatible uAgent: enabled")
    print("  Chat Protocol: enabled")
    print("  Agent details publishing: enabled")
    print("  Protocol manifest publishing: enabled")
    print()
    print("Inspector link:")
    print(inspector_link)
    print()
    print("Scenario memory:")
    print(f"  Initial: {SCENE_MEMORY['initial']}")
    print(f"  Later:   {SCENE_MEMORY['later']}")
    print()
    print("AURA tool modes:")
    print("  AURA_Monitor  - change detection and object movement")
    print("  AURA_Simulate - event reconstruction")
    print("  AURA_Inform   - factual scene context")
    print("  AURA_Guide    - next-step guidance")
    print()
    print("Start by saying:")
    print('  "hi"')
    print()


agent.include(protocol, publish_manifest=True)


if __name__ == "__main__":
    agent.run()
