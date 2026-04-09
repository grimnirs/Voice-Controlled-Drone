from enum import Enum

class DroneState(Enum):
    GROUNDED = "grounded"
    ARMED = "armed"
    AIRBORNE = "airborne"
    LANDING = "landing"

class StateMachine: #Implementera kill-switch, alla states kan gå till grounded omedelbart.
    TRANSITIONS = {
        DroneState.GROUNDED: [DroneState.ARMED],
        DroneState.ARMED: [DroneState.GROUNDED, DroneState.AIRBORNE],
        DroneState.AIRBORNE: [DroneState.LANDING], #Airborne --> Airborne? Just nu implicit definerat
        DroneState.LANDING: [DroneState.GROUNDED],
    }

    ALLOWED_COMMANDS = {
        DroneState.GROUNDED: ["arm"],
        DroneState.ARMED: ["disarm", "takeoff"],
        DroneState.AIRBORNE: ["land", "move", "goto", "stop", "set_velocity"],
        DroneState.LANDING: [],
    }

    def __init__(self):
        self.state = DroneState.GROUNDED

    def get_state(self) -> DroneState:
        return self.state

    def can_transition(self, new_state: DroneState) -> bool:
        return new_state in self.TRANSITIONS[self.state]

    def transition(self, new_state: DroneState) -> None:
        if not self.can_transition(new_state):
            raise ValueError(
                f"Cannot transition from {self.state.value} to {new_state.value}"
            )
        self.state = new_state

    def can_execute(self, command: str) -> bool:
        return command in self.ALLOWED_COMMANDS[self.state]


if __name__ == "__main__":
    sm = StateMachine()

    # Initial state
    assert sm.get_state() == DroneState.GROUNDED

    # Valid lifecycle: GROUNDED → ARMED → AIRBORNE → LANDING → GROUNDED
    sm.transition(DroneState.ARMED)
    assert sm.get_state() == DroneState.ARMED

    sm.transition(DroneState.AIRBORNE)
    assert sm.get_state() == DroneState.AIRBORNE

    sm.transition(DroneState.LANDING)
    assert sm.get_state() == DroneState.LANDING

    sm.transition(DroneState.GROUNDED)
    assert sm.get_state() == DroneState.GROUNDED

    # Invalid transition: GROUNDED → AIRBORNE
    try:
        sm.transition(DroneState.AIRBORNE)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass

    # can_execute: move only allowed when AIRBORNE
    assert not sm.can_execute("move")
    sm.transition(DroneState.ARMED)
    assert not sm.can_execute("move")
    sm.transition(DroneState.AIRBORNE)
    assert sm.can_execute("move")

    print("All tests passed!")