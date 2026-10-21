"""LiveKit entrypoint. `lk agent console|dev|start` run this file."""

from livekit.agents import cli

from medical_secretary.server import server

if __name__ == "__main__":
    cli.run_app(server)
