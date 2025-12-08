# pythonic-general-multicast

A basic UDP implementation with Docker Compose that demonstrates data streaming between senders via a server.

## Architecture

```
┌────────┐    UDP     ┌────────┐    UDP     ┌──────────┐
│ Sender │ ────────► │ Server │ ────────► │ Receiver │
└────────┘  (random   └────────┘  (forward  └──────────┘
            numbers)              data)
```

- **Sender**: Sends random numbers (1-1000) via UDP to the server
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

# Terminal 3: Start the sender
SERVER_HOST=localhost SERVER_PORT=5000 python src/sender.py
```

## Development

### Setup Development Environment

```bash
# Install development dependencies
pip install -r requirements-dev.txt
```

### Running Tests and Checks

This project uses [tox](https://tox.wiki/) for testing and code quality checks:

```bash
# Run all checks (format, lint, typecheck, docker tests)
tox

# Run specific environments
tox -e format      # Check code formatting with ruff
tox -e lint        # Run pylint
tox -e typecheck   # Run mypy type checking
tox -e docker      # Run Docker Compose system tests

# Run multiple environments
tox -e format,lint,typecheck

# List all available environments
tox -l
```

### Manual Testing

Run the system tests inside Docker containers:

```bash
# Using the shell script (deprecated, use tox instead)
./run_tests.sh

# Or manually with docker compose
docker compose run --rm test
```

The tests verify:
- All services can communicate over the Docker network
- Data packets contain proper SPM (Source Path Message) sequence numbers
- End-to-end data flow from sender → server → receiver

## Configuration

### Sender Environment Variables

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

## Packet Format

Data packets use JSON format with SPM (Source Path Message) for packet loss detection:

```json
{
  "spm": 123,      // Monotonically increasing sequence number
  "data": 456      // Actual data payload
}
```

## License

MIT License - see [LICENSE](LICENSE) for details.