"""One RGBW request at a time; no port opens on import."""
import argparse
import time
from color_mapper import rgbw_to_serial


class SerialSender:
    def __init__(self, port):
        self.port = port
        self.serial = None

    def __enter__(self):
        import serial
        self.serial = serial.Serial(
            port=None, baudrate=115200, timeout=0.1, write_timeout=2,
            xonxoff=False, rtscts=False, dsrdtr=False,
        )
        self.serial.dtr = False
        self.serial.rts = False
        self.serial.port = self.port
        try:
            self.serial.open()
            # Some USB bridges still reset the board when opening the port.
            time.sleep(2.5)
            self.serial.reset_input_buffer()
            self._exchange(b"PING\n", "READY", 5)
        except Exception:
            self.serial.close()
            raise
        return self

    def _exchange(self, payload, expected, timeout=2):
        if self.serial is None or not self.serial.is_open:
            raise RuntimeError("SerialSender must be used inside a with block")
        if self.serial.write(payload) != len(payload):
            raise OSError("Incomplete serial write; LED state is unknown")
        deadline = time.monotonic() + timeout
        pending = bytearray()
        while time.monotonic() < deadline:
            data = self.serial.read(1)
            if not data:
                continue
            if data == b"\n":
                line = pending.decode("ascii", errors="replace").rstrip("\r")
                pending.clear()
                if line == expected:
                    return line
                if line.startswith("ERR"):
                    raise RuntimeError(line)
                # Ignore boot messages, but never treat them as an ACK.
            else:
                pending.extend(data)
                if len(pending) > 128:
                    raise RuntimeError("Oversized serial response")
        raise TimeoutError("No matching ESP32 ACK; LED state is unknown")

    def send_speed(self, period_ms):
        if type(period_ms) is not int or not 900 <= period_ms <= 6000:
            raise ValueError("Flow period must be an integer in 900..6000 ms")
        try:
            return self._exchange(f"SPEED,{period_ms}\n".encode("ascii"), f"OK,SPEED,{period_ms}")
        except RuntimeError as exc:
            raise RuntimeError(f"Speed command rejected; upload the new adaptive LED sketch first: {exc}") from exc

    def send_top3(self, colors, period_ms):
        if len(colors) != 3:
            raise ValueError("Three ranked colors are required")
        if type(period_ms) is not int or not 600 <= period_ms <= 2400:
            raise ValueError("Top-three period must be in 600..2400 ms")
        fields = []
        for color in colors:
            rgbw_to_serial(color)
            if color[3] != 0 or max(color[:3]) == 0:
                raise ValueError("Ranked colors need nonzero RGB and W=0")
            fields.extend(str(v) for v in color[:3])
        message = "TOP," + ",".join(fields) + f",{period_ms}"
        return self._exchange((message + "\n").encode("ascii"), "OK," + message)

    def send_row(self, row, rgbw, period_ms=3200):
        if type(row) is not int or not 1 <= row <= 3:
            raise ValueError("Row must be 1, 2, or 3")
        if type(period_ms) is not int or not 900 <= period_ms <= 6000:
            raise ValueError("Flow period must be an integer in 900..6000 ms")
        color = rgbw_to_serial(rgbw).rstrip("\n")
        message = f"ROW,{row},{color},{period_ms}"
        return self._exchange((message + "\n").encode("ascii"), "OK," + message)

    def send_rgbw(self, rgbw):
        message = rgbw_to_serial(rgbw)
        return self._exchange(message.encode("ascii"), "OK," + message.rstrip("\n"))

    def __exit__(self, *args):
        if self.serial is not None:
            self.serial.close()


def send_rgbw(rgbw, port, baudrate=115200):
    """Compatibility with the original project's function API."""
    if baudrate != 115200:
        raise ValueError("The ESP32 firmware uses 115200 baud")
    with SerialSender(port) as sender:
        return sender.send_rgbw(rgbw)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--list-ports", action="store_true")
    parser.add_argument("--port")
    parser.add_argument("--rgbw", nargs=4, type=int, metavar=("R", "G", "B", "W"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        if args.list_ports:
            from serial.tools import list_ports
            for port in list_ports.comports():
                print(port.device, port.description)
            return
        if args.rgbw is None:
            parser.error("--rgbw R G B W is required")
        message = rgbw_to_serial(args.rgbw)
        if args.dry_run:
            print(repr(message))
            return
        if not args.port:
            parser.error("--port is required unless --dry-run is used")
        with SerialSender(args.port) as sender:
            print(sender.send_rgbw(args.rgbw))
    except (OSError, ValueError, RuntimeError, ImportError) as exc:
        parser.exit(1, f"Serial error: {exc}\n")


if __name__ == "__main__":
    main()
