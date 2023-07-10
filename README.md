# lanmessenger

A basic chat tool for discovering and messaging other people on your LAN.

This implementation is in Python and has 3 layers:

The network layer uses ZeroMQ PUB/SUB to communicate with other clients.

The discovery layer uses Zeroconf to publish the port our local service listens on, and discover peers
on the network. We use python-zeroconf to avoid needing an external Bonjour client dependency.

The UI layer uses dearpygui to implement a simple UI.

The application uses queues to pass messages around between the different layers and avoid thread safety issues.