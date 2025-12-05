# pythonic-general-multicast

A basic UDP implementation with Docker Compose that demonstrates data streaming between clients via a server.

## Architecture

```
┌────────┐    UDP     ┌────────┐    UDP     ┌──────────┐
│ Client │ ────────► │ Server │ ────────► │ Receiver │
└────────┘  (random   └────────┘  (forward  └──────────┘
            numbers)              data)
```

- **Client**: Sends random numbers (1-1000) via UDP to the server
- **Server**: Receives UDP data and forwards it to the receiver
- **Receiver**: Listens for and displays forwarded UDP data

## Quick Start

### Using Docker Compose

```bash
# Build and start all services
docker compose up --build

# Run in detached mode
docker compose up --build -d

# View logs
docker compose logs -f

# Stop all services
docker compose down
```

### Running Locally (without Docker)

Start each component in a separate terminal:

```bash
# Terminal 1: Start the receiver
LISTEN_PORT=5001 python src/receiver.py

# Terminal 2: Start the server
LISTEN_PORT=5000 FORWARD_HOST=localhost FORWARD_PORT=5001 python src/server.py

# Terminal 3: Start the client
SERVER_HOST=localhost SERVER_PORT=5000 python src/client.py
```

## Configuration

### Client Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVER_HOST` | `localhost` | Server hostname |
| `SERVER_PORT` | `5000` | Server UDP port |
| `SEND_INTERVAL` | `1.0` | Interval between sends (seconds) |

### Server Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LISTEN_HOST` | `0.0.0.0` | Host to listen on |
| `LISTEN_PORT` | `5000` | Port to listen on |
| `FORWARD_HOST` | `localhost` | Forward destination host |
| `FORWARD_PORT` | `5001` | Forward destination port |

### Receiver Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LISTEN_HOST` | `0.0.0.0` | Host to listen on |
| `LISTEN_PORT` | `5001` | Port to listen on |

## License

MIT License - see [LICENSE](LICENSE) for details.