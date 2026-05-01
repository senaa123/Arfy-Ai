import queue
from typing import Optional

from .audio.speech import listen
from .audio.tts_engine import speak
from .audio.wakeword import wait_for_wake_word
from .clients.agent_client import ask_agent, agent_health_check, end_agent_session
from .clients.memory_client import log_action, memory_health_check
from .local_actions.action_executor import execute_action
from .local_actions.intent_router import route_local_intent
from .session_state import create_session_id


class ArfyDesktopRuntime:
    """
    Always-running desktop runtime for Arfy.

    This class keeps the same desktop responsibilities as before:
    - session lifecycle
    - input mode switching
    - local desktop-only commands
    - agent request sending
    - wake loop control

    Phase 4B desktop cleanup:
    - remove global runtime variables from main.py
    - keep main.py as bootstrap only
    - preserve existing behavior while making the runtime easier to maintain

    Internal rule update:
    - clients/ = outbound API/service calls
    - integrations/ = local machine / Windows / process interaction
    """

    def __init__(self, *, app, window, ui):
        self.app = app
        self.window = window
        self.ui = ui

        self.typed_queue: queue.Queue[str] = queue.Queue() # create queue for typed msg
        self.input_mode = False #start voice mode
        self.current_session_id: Optional[str] = None

    def submit_text(self, text: str) -> None:
        """
        Receive typed input from the UI and queue it for the runtime loop.
        """
        self.typed_queue.put(text)

    # -------------------------
    # local system status check
    # -------------------------
    def handle_system_status_command(self, text: str) -> bool:
        """
        Handle explicit local system status requests.

        This is intentionally NOT routed through the agent.
        That keeps service checks out of normal conversation flow.
        """
        lower = text.lower().strip()

        trigger_phrases = [
            "check system status",
            "system status",
            "health check",
            "check the system status",
            "check status",
            "status report",
            "system report",
            "report of the system",
        ]

        keyword_match = (
            "system" in lower
            and ("status" in lower or "health" in lower or "report" in lower)
        )

        if not any(phrase in lower for phrase in trigger_phrases) and not keyword_match:
            return False

        agent_ok = agent_health_check()
        memory_ok = memory_health_check()

        report_lines = [
            "System status report.",
            f"Agent service: {'working' if agent_ok else 'not reachable'}.",
            f"Memory service: {'working' if memory_ok else 'not reachable'}.",
        ]

        response = " ".join(report_lines)

        print(response)
        self.ui.add_chat("Arfy", response)
        self.ui.set_state("speaking")
        speak(response)
        self.ui.set_state("listening" if not self.input_mode else "idle")

        return True

    # -------------------------
    # Input handling
    # -------------------------
    def get_input(self):
        """
        If in input mode, wait for typed text from the UI.
        Otherwise use voice input.
        """
        if self.input_mode:
            try:
                return self.typed_queue.get(timeout=60)
            except queue.Empty:
                return None
        else:
            return listen(time_limit=6)

    def finalize_current_session(self):
        """
        End the current session cleanly.
        """
        if not self.current_session_id:
            return

        result = end_agent_session(self.current_session_id)
        print(f"Session ended: {self.current_session_id}")
        print(f"Session archive result: {result}")

        self.current_session_id = None

    # -------------------------
    # Local desktop-only commands
    # -------------------------
    def handle_local_command(self, command: str):
        """
        Handle desktop-local commands that do not need the LLM.
        """
        if command == "switch_input_mode":
            self.input_mode = True
            self.ui.show_input()
            self.ui.set_mode_label("INPUT MODE")
            self.ui.set_state("speaking")
            speak("Switching to input mode!")
            self.ui.set_state("idle")
            return True

        if command == "switch_voice_mode":
            self.input_mode = False
            self.ui.hide_input()
            self.ui.set_mode_label("VOICE MODE")
            self.ui.set_state("speaking")
            speak("Switching to voice mode!")
            self.ui.set_state("listening")
            return True

        if command == "goodbye":
            self.input_mode = False
            self.ui.hide_input()
            self.ui.set_mode_label("VOICE MODE")

            self.finalize_current_session()

            self.ui.set_state("speaking")
            self.ui.add_chat("Arfy", "Goodbye Senaa!")
            speak("Goodbye Senaa!")
            self.ui.set_state("idle")
            return False

        if command == "shutdown":
            self.finalize_current_session()

            self.ui.set_state("speaking")
            speak("Shutting down! Bye Senaa!")
            self.app.quit()
            return False

        # Preserve current behavior for commands that are routed locally
        # but not yet implemented in the desktop shell.
        return True

    # -------------------------
    # Main command handling
    # -------------------------
    def handle_command(self, text):
        """
        Handle one user utterance during an active wake session.
        """
        if not text:
            return True

        if not self.current_session_id:
            self.current_session_id = create_session_id()

        normalized_text = text.strip().lower()

        if any(phrase in normalized_text for phrase in ["switch to input mode", "input mode"]):
            return self.handle_local_command("switch_input_mode")

        if any(phrase in normalized_text for phrase in ["switch to voice mode", "voice mode"]):
            return self.handle_local_command("switch_voice_mode")

        if any(phrase in normalized_text for phrase in ["let me type", "i'll type", "let me write"]):
            self.ui.set_state("speaking")
            speak("Sure, go ahead and type!")
            self.ui.show_input()
            self.ui.set_state("idle")

            try:
                text = self.typed_queue.get(timeout=30)
                normalized_text = text.strip().lower()
                self.ui.hide_input()
            except queue.Empty:
                self.ui.hide_input()
                speak("You didn't type anything.")
                return True

        self.ui.add_chat("You", text)

        if any(word in normalized_text for word in ["goodbye", "sleep", "seeyou"]):
            return self.handle_local_command("goodbye")

        if any(word in normalized_text for word in ["stop", "exit", "quit"]):
            return self.handle_local_command("shutdown")

        # NEW:
        # Run local system status check only when explicitly requested.
        if self.handle_system_status_command(text):
            return True

        local_result = route_local_intent(normalized_text)
        if local_result is not None:
            command = local_result.get("command")
            return self.handle_local_command(command)

        self.ui.set_state("thinking")

        # Only does the UI/Input work
        result = ask_agent(
            text=normalized_text,
            session_id=self.current_session_id,
        )

        response = result.get("response", "Sorry, I couldn't reach the agent service.")
        action = result.get("action")

        # Debug prints are useful while testing
        print("USER TEXT:", normalized_text)
        print("AGENT RESULT:", result)
        print("ACTION FROM AGENT:", action)

        if action:
            success, action_message = execute_action(action)

            log_action(
                action=str(action),
                action_type=action.get("type", "unknown"),
                success=success,
            )

            print(action_message)

            # For normal actions, only replace spoken reply if execution failed.
            if not success:
                response = action_message

        self.ui.set_state("speaking")
        print(f"Arfy [{self.current_session_id}]: {response}")
        self.ui.add_chat("Arfy", response)
        speak(response)

        self.ui.set_state("listening" if not self.input_mode else "idle")
        return True

    # -------------------------
    # Main assistant loop
    # -------------------------
    def arfy_loop(self):
        """
        Main wake-loop for Arfy.
        """
        if not agent_health_check():
            print("⚠️ Agent service not running")
            speak("Warning! Agent service is not running.")

        if not memory_health_check():
            print("⚠️ Memory service not running")
            speak("Warning! Memory service is not running.")

        self.ui.set_state("speaking")
        speak("Hello! I am Arfy, your personal assistant!")
        self.ui.set_state("idle")

        while True:
            result = wait_for_wake_word()

            if result == "shutdown":
                self.finalize_current_session()
                self.ui.set_state("speaking")
                speak("Shutting down! Bye Senaa!")
                self.app.quit()
                return

            elif result == "wake":
                self.current_session_id = create_session_id()
                print(f"New session started: {self.current_session_id}")

                self.ui.set_state("speaking")
                speak("Yes Senaa!")
                self.ui.set_state("listening")

                active_chat = True

                while active_chat:
                    self.ui.set_state("idle" if self.input_mode else "listening")

                    text = self.get_input()
                    if not text:
                        continue

                    active_chat = self.handle_command(text)
