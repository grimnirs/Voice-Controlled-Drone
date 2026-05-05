# import asyncio
# import os
#from mavsdk import System
# from command_handler import txt_to_cmd, DroneCommand
#from mavsdk.offboard import VelocityBodyYawspeed
# from typing import TypedDict, Optional

from state.machine import StateMachine

latest_odom = None
sm = StateMachine()
