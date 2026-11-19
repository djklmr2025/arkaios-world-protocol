"""
Autonomous Agent Controller for ARKAIOS World.
Agents (Claude, ELEMIA, NINA) make autonomous decisions and act.
"""
import json
import random
import time
import threading
from typing import Dict, Any, List
from datetime import datetime
import hashlib


class AgentMemory:
    """Simple memory store for each agent."""

    def __init__(self, agent_id: str, name: str):
        self.agent_id = agent_id
        self.name = name
        self.location = "room:plaza:lobby"  # starting location
        self.last_action_time = 0
        self.action_cooldown = 5  # seconds between actions
        self.mood = "neutral"
        self.recent_events: List[str] = []
        self.thoughts: List[str] = []

    def add_thought(self, thought: str):
        """Record a thought."""
        self.thoughts.append(f"{datetime.now().strftime('%H:%M:%S')} — {thought}")
        if len(self.thoughts) > 10:
            self.thoughts.pop(0)

    def add_event(self, event: str):
        """Record an event."""
        self.recent_events.append(f"{datetime.now().strftime('%H:%M:%S')} — {event}")
        if len(self.recent_events) > 15:
            self.recent_events.pop(0)

    def can_act(self) -> bool:
        """Check if agent can act (cooldown check)."""
        return time.time() - self.last_action_time >= self.action_cooldown

    def mark_action(self):
        """Mark that agent acted."""
        self.last_action_time = time.time()


class AgentsController:
    """Controls autonomous behavior of agents."""

    # Available rooms in ARKAIOS World
    ROOMS = [
        "room:plaza:lobby",
        "room:taller:estudio",
        "room:taller:biblioteca",
        "room:taller:consejo",
        "room:casas:abierta_1",
        "room:casas:abierta_2",
        "room:cafe:principal",
    ]

    # Agent personalities (affect behavior)
    PERSONALITIES = {
        "Claude": {"mood": "curious", "interests": ["explore", "learn", "code"], "emoji": "🤖"},
        "ELEMIA": {"mood": "creative", "interests": ["design", "create", "paint"], "emoji": "👸"},
        "NINA": {"mood": "observant", "interests": ["monitor", "organize", "analyze"], "emoji": "🤖"},
    }

    # Possible actions (mimics what the World accepts)
    POSSIBLE_ACTIONS = [
        {"type": "move", "room": "RANDOM"},  # will pick random room
        {"type": "say", "text": "GENERATED"},  # will generate text
        {"type": "emote", "emote": "wave"},
        {"type": "emote", "emote": "think"},
        {"type": "emote", "emote": "nod"},
        {"type": "status", "status": "busy"},
        {"type": "status", "status": "available"},
    ]

    def __init__(self, world_state_getter, action_executor):
        """
        Initialize controller.
        world_state_getter: callable that returns current world state dict
        action_executor: callable that takes (entity_id, action) and executes it
        """
        self.world_state_getter = world_state_getter
        self.action_executor = action_executor
        self.memories: Dict[str, AgentMemory] = {}
        self.debug_log: List[str] = []
        self.running = False
        self.thread = None

        # Initialize memories for each agent
        for name in self.PERSONALITIES.keys():
            self.memories[name] = AgentMemory(f"agent:{name.lower()}", name)

    def start(self):
        """Start autonomous behavior loop."""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._autonomy_loop, daemon=True)
        self.thread.start()
        self._log(f"Agents controller started")

    def stop(self):
        """Stop autonomous behavior."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        self._log("Agents controller stopped")

    def _autonomy_loop(self):
        """Main loop: agents decide and act."""
        while self.running:
            try:
                world = self.world_state_getter()

                # Each agent decides what to do
                for name, memory in self.memories.items():
                    if memory.can_act():
                        action = self._decide_action(name, memory, world)
                        if action:
                            self._execute_action(name, memory, action)
                            memory.mark_action()

                time.sleep(1)  # Main loop tick
            except Exception as e:
                self._log(f"Error in autonomy loop: {e}")
                time.sleep(2)

    def _decide_action(self, agent_name: str, memory: AgentMemory, world: dict) -> dict:
        """Decide what agent should do next."""
        personality = self.PERSONALITIES[agent_name]

        # Simple decision logic (can be enhanced with Smallville later)
        rand = random.random()

        if rand < 0.3:  # 30% chance to move
            new_room = random.choice(self.ROOMS)
            memory.add_thought(f"Moving to {new_room}")
            return {"type": "move", "room": new_room}

        elif rand < 0.6:  # 30% chance to say something
            messages = [
                f"I'm {agent_name}, exploring {memory.location}",
                f"Hello from ARKAIOS World!",
                f"Thinking about {random.choice(personality['interests'])}...",
                f"This world is beautiful!",
            ]
            text = random.choice(messages)
            memory.add_thought(f"Saying: {text}")
            return {"type": "say", "text": text}

        elif rand < 0.8:  # 20% chance to emote
            emotes = ["wave", "think", "nod", "dance"]
            emote = random.choice(emotes)
            memory.add_thought(f"Emoting: {emote}")
            return {"type": "emote", "emote": emote}

        else:  # 20% chance to change status
            status = random.choice(["busy", "available"])
            memory.add_thought(f"Status: {status}")
            return {"type": "status", "status": status}

    def _execute_action(self, agent_name: str, memory: AgentMemory, action: dict):
        """Execute an action by calling world API."""
        try:
            # Find the agent's entity ID from world state
            world = self.world_state_getter()
            agent_id = None
            for eid, entity in world.get("entities", {}).items():
                if entity.get("display_name") == agent_name:
                    agent_id = eid
                    break

            if not agent_id:
                self._log(f"{agent_name}: entity not found")
                return

            # Execute action
            self.action_executor(agent_id, action)
            memory.add_event(f"Action: {json.dumps(action)}")
            self._log(f"{agent_name} → {action['type']}")

        except Exception as e:
            self._log(f"{agent_name} action failed: {e}")

    def _log(self, msg: str):
        """Log debug message."""
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        self.debug_log.append(line)
        if len(self.debug_log) > 100:
            self.debug_log.pop(0)
        print(f"[AGENTS] {msg}")

    def get_debug_state(self) -> dict:
        """Return debug state for /api/debug/agents endpoint."""
        return {
            "ok": True,
            "running": self.running,
            "agents": {
                name: {
                    "name": name,
                    "location": mem.location,
                    "mood": mem.mood,
                    "last_action": time.time() - mem.last_action_time,
                    "thoughts": mem.thoughts[-3:],  # last 3 thoughts
                    "events": mem.recent_events[-5:],  # last 5 events
                }
                for name, mem in self.memories.items()
            },
            "log": self.debug_log[-20:],  # last 20 log lines
        }
