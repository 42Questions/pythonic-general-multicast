# CLAUDE.md - AI Assistant Guide

This document provides comprehensive guidance for AI assistants working with the `pythonic-general-multicast` codebase.

## Project Overview

**pythonic-general-multicast** is a UDP-based data streaming implementation that demonstrates client-server-receiver architecture using Python and Docker. The project showcases:

- UDP socket programming with Python's `socket` module
- Docker Compose orchestration for multi-service networking
- Source Path Message (SPM) sequence numbering for packet tracking
- Modern Python development practices (Python 3.14+, type hints, strict linting)

**Key Technologies:**
- Python 3.14+ (latest features, strict typing)
- Docker & Docker Compose (containerization)
- pytest (testing)
- ruff (formatting/linting), pylint (linting), mypy (type checking)
- tox (test orchestration)

## Codebase Structure

```
pythonic-general-multicast/
├── src/                      # Main source code
│   ├── client.py            # UDP client (sends random data)
│   ├── server.py            # UDP server (forwards data)
│   ├── receiver.py          # UDP receiver (displays data)
│   └── config.py            # Configuration (currently minimal)
├── tests/                    # Test suite
│   ├── __init__.py
│   └── test_system.py       # Docker-based system integration tests
├── docker-compose.yml        # Multi-service orchestration
├── Dockerfile               # Container definition (Python 3.14-slim)
├── pyproject.toml           # Project metadata and tool configs
├── tox.ini                  # Test automation configuration
├── requirements-dev.txt     # Development dependencies
├── .gitignore               # Git ignore patterns
├── LICENSE                  # MIT License
└── README.md                # User-facing documentation

Key Files:
- src/client.py:17-64        # Sender class (context manager pattern)
- src/server.py:11-46        # Server main loop with forwarding logic
- src/receiver.py:11-33      # Receiver main loop
- tests/test_system.py:8-50  # System integration tests
```

## Architecture

### Data Flow

```
┌────────┐    UDP     ┌────────┐    UDP     ┌──────────┐
│ Client │ ────────► │ Server │ ────────► │ Receiver │
└────────┘  (random   └────────┘  (forward  └──────────┘
            numbers)              data)
```

### Network Design

**Docker Network:** All services communicate via a bridge network (`udp-network`)

**Service Dependencies:**
- `receiver` → standalone (starts first)
- `server` → depends on `receiver`
- `client` → depends on `server`
- `test` → depends on all three services

**Port Allocation:**
- Server listens on: `5000` (UDP)
- Receiver listens on: `5001` (UDP)
- Test socket (optional): `5002` (UDP)

### Packet Format

All UDP packets use JSON encoding with SPM (Source Path Message) tracking:

```json
{
  "spm": 123,      // Monotonically increasing sequence number
  "data": 456      // Actual payload (random int 1-10 for client)
}
```

**Key Characteristics:**
- UTF-8 encoded JSON
- 1024-byte buffer size
- No acknowledgments (fire-and-forget UDP)
- Sequence numbers increment per packet (client-side)

## Development Workflows

### Initial Setup

```bash
# Clone repository
git clone <repo-url>
cd pythonic-general-multicast

# Install development dependencies
pip install -r requirements-dev.txt
```

### Running Services

**With Docker Compose (recommended):**
```bash
docker compose up --build          # Build and run all services
docker compose up --build -d       # Detached mode
docker compose logs -f             # Follow logs
docker compose down                # Stop and remove containers
```

**Locally (without Docker):**
```bash
# Terminal 1: Receiver
LISTEN_PORT=5001 python src/receiver.py

# Terminal 2: Server
LISTEN_PORT=5000 FORWARD_HOST=localhost FORWARD_PORT=5001 python src/server.py

# Terminal 3: Client
SERVER_HOST=localhost SERVER_PORT=5000 python src/client.py
```

### Testing & Quality Checks

**Using tox (recommended):**
```bash
tox                    # Run all checks (format, lint, typecheck, docker tests)
tox -e format          # Check formatting with ruff
tox -e lint            # Run pylint
tox -e typecheck       # Run mypy type checking
tox -e docker          # Run Docker system tests
tox -e all             # Run all checks sequentially
```

**Manual Docker Testing:**
```bash
docker compose run --rm test      # Run pytest in container
```

### Git Workflow

**Branching:**
- Main branch: `main` (or unspecified)
- Feature branches: Follow naming convention (e.g., `claude/feature-name`)

**Commit Messages:**
- Concise, imperative style
- Examples from history:
  - "Added docker system test, and re-factored client.py"
  - "Add basic UDP implementation with Docker Compose (#1)"

**Important:** Always verify branch name before pushing. AI assistants should work on designated feature branches.

## Code Conventions

### Python Style (enforced by ruff & pylint)

**Line Length:** 100 characters max (pyproject.toml:10)

**Import Order:** Follows isort standards (ruff handles this)
```python
# Standard library
import json
import logging
import os

# Third-party (if any)
# ...

# Local imports
from collections.abc import Callable
```

**Type Hints:** Required for all function signatures (mypy strict mode)
```python
def send_data(self, send_func: Callable[[], int]) -> None:
    """Type hints are mandatory."""
```

**Docstrings:** Only module-level docstrings required (see src/client.py:1)
- Format: Triple double-quotes
- Style: One-line summary for simple modules

**Naming Conventions:**
- Functions/methods: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private variables: `_leading_underscore`
- Logger: `_LOGGER` (module-level constant)

**Logging Format:**
```python
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
_LOGGER = logging.getLogger(__name__)
```

### Architecture Patterns

**Context Managers:** Used for resource management (src/client.py:24-39)
```python
class Sender:
    def __enter__(self) -> Sender:
        """Initialize resources."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Clean up resources."""
        if self.sock:
            self.sock.close()
        return False
```

**Error Handling:**
- Graceful degradation (log errors, continue when possible)
- Specific exceptions (OSError for network, UnicodeDecodeError for decoding)
- KeyboardInterrupt handling for clean shutdown

**Configuration:**
- Environment variables via `os.environ.get()` with defaults
- No external config files (12-factor app style)

### Disabled Linting Rules

The following pylint rules are intentionally disabled (pyproject.toml:52-57):
- `missing-module-docstring` (only required in module header)
- `missing-class-docstring` (code is self-documenting)
- `missing-function-docstring` (type hints provide clarity)
- `too-few-public-methods` (dataclasses/simple classes are fine)

## Environment Variables

### Client (`src/client.py`)

| Variable | Type | Default | Description | Location |
|----------|------|---------|-------------|----------|
| `SERVER_HOST` | str | `localhost` | Server hostname/IP | client.py:68 |
| `SERVER_PORT` | int | `5000` | Server UDP port | client.py:69 |
| `SEND_INTERVAL` | float | `1.0` | Seconds between sends | client.py:70 |

### Server (`src/server.py`)

| Variable | Type | Default | Description | Location |
|----------|------|---------|-------------|----------|
| `LISTEN_HOST` | str | `0.0.0.0` | Bind address | server.py:13 |
| `LISTEN_PORT` | int | `5000` | Listen port | server.py:14 |
| `FORWARD_HOST` | str | `localhost` | Forward destination | server.py:15 |
| `FORWARD_PORT` | int | `5001` | Forward port | server.py:16 |

### Receiver (`src/receiver.py`)

| Variable | Type | Default | Description | Location |
|----------|------|---------|-------------|----------|
| `LISTEN_HOST` | str | `0.0.0.0` | Bind address | receiver.py:13 |
| `LISTEN_PORT` | int | `5001` | Listen port | receiver.py:14 |

**Docker Overrides:** See docker-compose.yml:5-9, 18-21, 30-32 for container-specific settings.

## Testing Strategy

### Test Structure

**System Integration Tests:** `tests/test_system.py`
- Runs inside Docker containers
- Tests end-to-end data flow
- Verifies service connectivity

**Test Functions:**
- `test_receiver_gets_data_from_client()` (test_system.py:8-32)
  - Validates receiver reachability
  - Confirms server forwarding chain
  - Uses 3-second stabilization delay

- `test_data_flow_with_sequence_numbers()` (test_system.py:35-50)
  - Validates SPM sequence numbering
  - Tests socket binding on port 5002

### Running Tests

**Preferred Method (tox):**
```bash
tox -e docker     # Automated: build, start services, test, cleanup
```

**Manual Method:**
```bash
docker compose up --build -d client server receiver
sleep 3
docker compose run --rm test
docker compose down
```

**Test Output:**
- pytest verbose mode (`-v -s`)
- Print statements show test progress
- Checkmark bullets (✓) indicate success

## Key Design Decisions

### Why UDP?
- Low latency (no handshake)
- Simple forwarding logic
- Demonstrates packet loss scenarios
- Educational: shows trade-offs vs TCP

### Why Context Managers?
- Guarantees socket cleanup (src/client.py:24-39)
- Pythonic resource management
- Exception-safe

### Why JSON for Packets?
- Human-readable debugging
- Easy to extend with metadata
- Built-in Python support

### Why Docker Compose?
- Service orchestration
- Network isolation
- Reproducible environments
- Easy testing

### Why Python 3.14?
- Latest features (type system improvements)
- Modern async capabilities (not used yet, but available)
- Performance improvements

### Why Sequence Numbers (SPM)?
- Detect packet loss
- Verify ordering
- Debug network issues
- Future: could add acknowledgments

## Common Tasks for AI Assistants

### Adding a New Service

1. Create Python module in `src/`
2. Add service to `docker-compose.yml`
3. Define environment variables
4. Update this CLAUDE.md file
5. Add integration tests
6. Update README.md

### Modifying Packet Format

1. Update sender encoding (client.py:53-54)
2. Update receiver decoding (server.py:30, receiver.py:25)
3. Update test validation (test_system.py:15)
4. Document in README.md packet format section

### Adding New Configuration

1. Add `os.environ.get()` in relevant module
2. Update environment variables table (this file)
3. Add to docker-compose.yml
4. Update README.md configuration section
5. Provide sensible defaults

### Running Code Quality Checks

Before committing changes:
```bash
tox -e format,lint,typecheck    # Fast: skip Docker tests
tox                             # Full: includes Docker tests
```

Fix issues:
```bash
ruff format src/ tests/         # Auto-format code
ruff check --fix src/ tests/    # Auto-fix lint issues
mypy src/ tests/                # Check types (manual fixes needed)
```

### Debugging Network Issues

**View Service Logs:**
```bash
docker compose logs -f client    # Client logs only
docker compose logs -f server    # Server logs only
docker compose logs -f receiver  # Receiver logs only
docker compose logs -f           # All logs interleaved
```

**Inspect Network:**
```bash
docker compose exec server ip addr           # Check server IP
docker compose exec client ping server       # Test connectivity
docker compose exec server netstat -uln      # Check UDP listeners
```

**Manual Packet Sending:**
```python
import socket, json
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
packet = json.dumps({"spm": 999, "data": 123}).encode("utf-8")
sock.sendto(packet, ("localhost", 5000))
```

### Understanding Sequence Numbers

**Client-side (client.py:22, 53-58):**
- Initialized to `0` on startup
- Increments after each successful send
- Monotonically increasing (no resets)

**Server-side:**
- Forwards packets unchanged
- Does not validate sequence numbers
- No gap detection

**Test Validation (test_system.py:15):**
- Uses `spm: 999` for test packets
- Actual validation logic is minimal (future enhancement)

## AI Assistant Guidelines

### Do's

✅ **Read before modifying:** Always read existing files before making changes
✅ **Follow type hints:** Maintain strict typing (`mypy` enforces this)
✅ **Use context managers:** For any resource management (sockets, files)
✅ **Log errors gracefully:** Continue operation when possible
✅ **Update tests:** Add/modify tests for new functionality
✅ **Run tox before committing:** Ensure all checks pass
✅ **Update documentation:** Keep CLAUDE.md and README.md in sync
✅ **Respect environment variables:** Don't hardcode configuration
✅ **Use existing patterns:** Follow established code style
✅ **Check Docker logs:** When debugging integration issues

### Don'ts

❌ **Don't skip type hints:** All functions need proper signatures
❌ **Don't hardcode values:** Use environment variables with defaults
❌ **Don't ignore test failures:** Fix issues before proceeding
❌ **Don't mix concerns:** Keep client/server/receiver separate
❌ **Don't add heavy dependencies:** Keep the project lightweight
❌ **Don't break Docker networking:** Test changes with `tox -e docker`
❌ **Don't commit without formatting:** Run `ruff format` first
❌ **Don't violate line length:** 100 characters max
❌ **Don't add unnecessary abstractions:** Keep it simple
❌ **Don't use TCP:** This is intentionally UDP-focused

### When Making Changes

**Small Changes (single file, <50 lines):**
1. Read the file
2. Make changes
3. Run `tox -e format,lint,typecheck`
4. Test manually if needed
5. Commit

**Medium Changes (multiple files, new feature):**
1. Read relevant files
2. Update code
3. Add/update tests
4. Run full `tox`
5. Update CLAUDE.md if needed
6. Update README.md
7. Commit

**Large Changes (architecture, new service):**
1. Discuss approach first
2. Read all relevant files
3. Make incremental changes
4. Test after each increment
5. Update all documentation
6. Run full `tox`
7. Consider adding examples
8. Commit in logical chunks

### Debugging Checklist

When investigating issues:

- [ ] Check Docker logs (`docker compose logs -f`)
- [ ] Verify environment variables (docker-compose.yml)
- [ ] Confirm network connectivity (ping between containers)
- [ ] Validate packet format (JSON structure)
- [ ] Check port bindings (netstat)
- [ ] Review sequence numbers (SPM field)
- [ ] Test with manual packet sending
- [ ] Verify service startup order (depends_on)
- [ ] Check for Unicode errors (UTF-8 encoding)
- [ ] Review error logs for OSError exceptions

### Code Review Focus Areas

When reviewing code:

- **Type Safety:** All functions have type hints, mypy passes
- **Error Handling:** OSError, UnicodeDecodeError caught appropriately
- **Resource Cleanup:** Sockets closed in finally blocks or `__exit__`
- **Logging:** Appropriate log levels (INFO for normal, ERROR for issues)
- **Environment Variables:** All configs have defaults
- **Docker Compatibility:** Services communicate via hostnames (not localhost)
- **Test Coverage:** New features have integration tests
- **Documentation:** CLAUDE.md and README.md updated
- **Code Style:** ruff and pylint pass without errors
- **Line Length:** No lines exceed 100 characters

## Project Roadmap & Future Enhancements

**Potential Areas for Improvement** (not yet implemented):

1. **Packet Loss Detection:** Validate SPM gaps in receiver
2. **Acknowledgment System:** Add TCP-like reliability to UDP
3. **Multiple Clients:** Support multiple senders
4. **Data Persistence:** Log received packets to file/database
5. **Metrics Dashboard:** Real-time packet statistics
6. **Protocol Buffers:** Replace JSON for efficiency
7. **Compression:** Add gzip for larger payloads
8. **Authentication:** Add HMAC or encryption
9. **Rate Limiting:** Prevent flooding
10. **Health Checks:** Docker healthcheck endpoints

**If implementing new features, consider:**
- Maintain backward compatibility with existing packet format
- Keep Docker setup simple
- Add comprehensive tests
- Update documentation first (README-driven development)

## Troubleshooting

### Common Issues

**"Address already in use"**
- Stop existing containers: `docker compose down`
- Check for orphaned processes: `lsof -i :5000`

**"Name or service not known"**
- Use Docker service names (e.g., `server`, not `localhost`)
- Verify docker-compose.yml network configuration

**"No route to host"**
- Ensure all services are on `udp-network`
- Check `depends_on` startup order

**"Received invalid UTF-8 data"**
- Verify sender uses `.encode("utf-8")`
- Check packet format matches JSON structure

**Tests fail with timeout**
- Increase sleep duration in test_system.py:11
- Check service logs for startup errors

## Additional Resources

- **Python socket programming:** https://docs.python.org/3/library/socket.html
- **Docker Compose networking:** https://docs.docker.com/compose/networking/
- **Ruff formatter:** https://docs.astral.sh/ruff/
- **Mypy type checking:** https://mypy.readthedocs.io/
- **Tox automation:** https://tox.wiki/

## Document Maintenance

**Last Updated:** 2025-12-08
**Python Version:** 3.14
**Docker Compose Version:** 2.x

**Update Triggers:**
- New services added
- Packet format changes
- Environment variable additions
- Architecture modifications
- Testing strategy changes
- Tool configuration updates

**Maintainers:** AI assistants should keep this document in sync with code changes.
