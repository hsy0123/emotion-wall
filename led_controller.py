"""Optional USB output. Owns one serial connection and serializes LED commands."""
from threading import Lock

from serial_sender import SerialSender


class LedController:
    def __init__(self, port=None, sender_factory=SerialSender):
        self.port = port
        self._sender_factory = sender_factory
        self._sender = None
        self._lock = Lock()

    def display(self, motion):
        status = {"enabled": bool(self.port), "sent": False}
        if not self.port:
            return status
        with self._lock:
            try:
                if self._sender is None:
                    self._sender = self._sender_factory(self.port).__enter__()
                colors = motion["top_colors"]
                period = motion["flow_period_ms"]
                top_period = motion["top_flow_period_ms"]
                ack = self._sender.send_top3(colors, top_period)
                self._sender.send_row(2, colors[0], period)
                self._sender.send_row(3, colors[0], period)
                status.update(
                    sent=True, rgbw=colors[0], ack=ack, flow_period_ms=period,
                    top_emotions=motion["top_emotions"], top_colors=colors,
                    left_flow_period_ms=top_period,
                )
            except (OSError, ValueError, RuntimeError, ImportError, KeyError, TypeError) as error:
                self._disconnect()
                status["error"] = str(error)
        return status

    def _disconnect(self):
        if self._sender is not None:
            try:
                self._sender.__exit__(None, None, None)
            finally:
                self._sender = None

    def close(self):
        with self._lock:
            self._disconnect()
