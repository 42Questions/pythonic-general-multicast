"""PGM DLR (Designated Local Repairer) with multi-threaded processing."""
import logging
import os
import socket
import threading
import time
from dataclasses import dataclass
from enum import Enum, auto
from queue import Empty, Queue
from types import TracebackType

from src.base import NetworkParticipant, RepairCache
from src.protocol import PacketType, PGMPacket, UserPayload

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
_LOGGER = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of messages in the processing queue."""

    DATA = auto()
    NAK_BATCH = auto()


@dataclass
class DataMessage:
    """Message containing DATA packet information."""

    sequence: int
    packet_bytes: bytes


@dataclass
class NakBatchMessage:
    """Message containing aggregated NAK requests."""

    sequences: set[int]


@dataclass
class QueueMessage:
    """Wrapper for messages in the processing queue."""

    msg_type: MessageType
    data_msg: DataMessage | None = None
    nak_msg: NakBatchMessage | None = None


class DLR(NetworkParticipant):
    """PGM DLR with multi-threaded MPSC queue.

    3 threads: data listener, NAK listener (aggregates 0.01s), processor.
    """

    def __init__(
        self,
        listen_host: str,
        listen_port: int,
        nak_listen_host: str,
        nak_listen_port: int,
        forwarder_host: str,
        forwarder_port: int,
        repair_cache_size: int,
        nak_aggregation_interval: float,
    ) -> None:
        super().__init__()
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.nak_listen_host = nak_listen_host
        self.nak_listen_port = nak_listen_port
        self.forwarder_host = forwarder_host
        self.forwarder_port = forwarder_port
        self.nak_aggregation_interval = nak_aggregation_interval

        self.processing_queue: Queue[QueueMessage] = Queue()
        self.repair_cache = RepairCache(_max_size=repair_cache_size)

        self.data_sock: socket.socket | None = None
        self.nak_sock: socket.socket | None = None
        self.repair_sock: socket.socket | None = None

        self.stop_event = threading.Event()
        self.threads: list[threading.Thread] = []

        _LOGGER.info(f"DLR initialized: data={listen_host}:{listen_port}, "
                     f"nak={nak_listen_host}:{nak_listen_port}, "
                     f"repair={forwarder_host}:{forwarder_port}")

    def __enter__(self) -> DLR:
        self.data_sock = self._create_socket()
        self.data_sock.bind((self.listen_host, self.listen_port))
        self.data_sock.settimeout(0.1)

        self.nak_sock = self._create_socket()
        self.nak_sock.bind((self.nak_listen_host, self.nak_listen_port))
        self.nak_sock.settimeout(0.1)

        self.repair_sock = self._create_socket()

        self.stop_event.clear()
        self.threads = [
            threading.Thread(target=self._data_listener_loop, name="DataListener"),
            threading.Thread(target=self._nak_listener_loop, name="NAKListener"),
            threading.Thread(target=self._processor_loop, name="Processor"),
        ]
        for t in self.threads:
            t.start()

        _LOGGER.info("DLR threads started")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        _LOGGER.info("Stopping DLR...")
        self.stop_event.set()

        timeouts = [2.0, 2.0, 5.0]  # data, nak, processor
        for thread, timeout in zip(self.threads, timeouts):
            thread.join(timeout=timeout)
            if thread.is_alive():
                _LOGGER.warning(f"{thread.name} did not stop in time")
        for s in [self.data_sock, self.nak_sock, self.repair_sock]:
            self._close_socket(s)

        _LOGGER.info("DLR stopped")
        return False

    def run(self) -> None:
        """Run DLR main loop (blocks until KeyboardInterrupt)."""
        try:
            _LOGGER.info("DLR running... Press Ctrl+C to stop")
            while True:
                time.sleep(1.0)
        except KeyboardInterrupt:
            _LOGGER.info("DLR interrupted by user")

    def _data_listener_loop(self) -> None:
        _LOGGER.info("Data listener started")
        assert self.data_sock is not None  # Guaranteed by __enter__

        while not self.stop_event.is_set():
            try:
                data, _ = self.data_sock.recvfrom(2048)
                packet = PGMPacket.unpack(data)

                if packet.packet_type == PacketType.DATA:
                    msg = QueueMessage(
                        msg_type=MessageType.DATA,
                        data_msg=DataMessage(sequence=packet.sequence, packet_bytes=data),
                    )
                    self.processing_queue.put(msg)
                    _LOGGER.debug(f"Queued DATA [SEQ: {packet.sequence}]")
                elif packet.packet_type == PacketType.SPM:
                    _LOGGER.debug(f"Received SPM [SEQ: {packet.sequence}] (ignored)")

            except socket.timeout:
                continue
            except (ValueError, OSError) as e:
                if not self.stop_event.is_set():
                    _LOGGER.error(f"Data listener error: {e}")

        _LOGGER.info("Data listener stopped")

    def _nak_listener_loop(self) -> None:
        _LOGGER.info("NAK listener started")
        assert self.nak_sock is not None  # Guaranteed by __enter__

        nak_buffer: set[int] = set()
        last_flush: float = time.time()

        while not self.stop_event.is_set():
            current_time = time.time()
            if current_time - last_flush >= self.nak_aggregation_interval:
                if nak_buffer:
                    msg = QueueMessage(
                        msg_type=MessageType.NAK_BATCH,
                        nak_msg=NakBatchMessage(sequences=nak_buffer.copy()),
                    )
                    self.processing_queue.put(msg)
                    _LOGGER.debug(f"Queued NAK batch: {len(nak_buffer)} sequences")
                    nak_buffer.clear()
                last_flush = current_time

            try:
                data, _ = self.nak_sock.recvfrom(2048)
                packet = PGMPacket.unpack(data)
                if packet.packet_type == PacketType.NAK and packet.requested_sequence is not None:
                    nak_buffer.add(packet.requested_sequence)

            except socket.timeout:
                pass
            except (ValueError, OSError) as e:
                if not self.stop_event.is_set():
                    _LOGGER.error(f"NAK listener error: {e}")

        if nak_buffer:
            msg = QueueMessage(
                msg_type=MessageType.NAK_BATCH,
                nak_msg=NakBatchMessage(sequences=nak_buffer),
            )
            self.processing_queue.put(msg)
            _LOGGER.debug(f"Flushed {len(nak_buffer)} NAKs on shutdown")

        _LOGGER.info("NAK listener stopped")

    def _process_message(self, msg: QueueMessage) -> None:
        """Process a queue message - either DATA or NAK batch."""
        if msg.msg_type == MessageType.DATA and msg.data_msg:
            self.repair_cache.add(msg.data_msg.sequence, msg.data_msg.packet_bytes)
            _LOGGER.info(f"Cached DATA [SEQ: {msg.data_msg.sequence}]")
        elif msg.msg_type == MessageType.NAK_BATCH and msg.nak_msg:
            assert self.repair_sock is not None  # Guaranteed by __enter__

            for seq in msg.nak_msg.sequences:
                if packet_data := self.repair_cache.get(seq):
                    try:
                        self.repair_sock.sendto(packet_data, (self.forwarder_host, self.forwarder_port))
                        _LOGGER.info(f"Sent repair [SEQ: {seq}]")
                    except OSError as e:
                        _LOGGER.error(f"Repair send failed [SEQ: {seq}]: {e}")
                else:
                    _LOGGER.warning(f"Cannot repair [SEQ: {seq}] - not in cache")

    def _processor_loop(self) -> None:
        _LOGGER.info("Processor started")

        while not self.stop_event.is_set():
            try:
                self._process_message(self.processing_queue.get(timeout=0.1))
                self.processing_queue.task_done()
            except Empty:
                continue

        _LOGGER.info("Draining queue...")
        while True:
            try:
                self._process_message(self.processing_queue.get_nowait())
                self.processing_queue.task_done()
            except Empty:
                break

        _LOGGER.info("Processor stopped")


class IntPayload(UserPayload):
    def __init__(self, value: int = 0) -> None:
        self.value = value

    def pack(self) -> bytes:
        return self.value.to_bytes(4, byteorder="big", signed=True)

    def unpack(self, data: bytes) -> None:
        if len(data) < 4:
            raise ValueError(f"Expected at least 4 bytes, got {len(data)}")
        self.value = int.from_bytes(data[:4], byteorder="big", signed=True)


def main() -> None:
    from src.constants import Settings

    settings = Settings()

    with DLR(
        os.environ.get("LISTEN_HOST", "0.0.0.0"),
        int(os.environ.get("LISTEN_PORT", "5001")),
        os.environ.get("NAK_LISTEN_HOST", "0.0.0.0"),
        int(os.environ.get("NAK_LISTEN_PORT", "5003")),
        os.environ.get("FORWARDER_HOST", "localhost"),
        int(os.environ.get("FORWARDER_PORT", "5000")),
        settings.REPAIR_CACHE_SIZE,
        settings.NAK_AGGREGATION_INTERVAL,
    ) as dlr:
        dlr.run()


if __name__ == "__main__":
    main()
