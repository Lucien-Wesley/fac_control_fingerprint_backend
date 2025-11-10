from __future__ import annotations

import threading
import time
from typing import List, Optional, Tuple, Iterator, Dict

import serial
import serial.tools.list_ports

STATUS_FILE_PATH = 'last_message.txt'


class ArduinoManager:
    """Arduino serial manager implementing the provided firmware protocol.

    Protocol (9600 bps):
      - Send commands:
          'V'                 -> switch to verification mode
          'E'                 -> switch to enrollment mode
          'I:<id>' or 'I<id>' -> set enrollment ID (0-127)
          'C'                 -> cancel current enrollment
      - Device messages (one per line, '\n' terminated):
          'VERIFICATION: EN_COURS | SUCCES ID trouve: <id> | ECHEC'
          'ENREGISTREMENT: EN_COURS | SUCCES | ECHEC | ABANDONNE'
          'ACK:...' | 'ERR:...' | 'INFO: ...' | 'PORTE: ...' | 'CAPTEUR: ...'
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.last_message = "Initialisation en cours..."
        self.message_lock = threading.Lock()
        self._ser: Optional[serial.Serial] = None
        self._port: Optional[str] = None
        self._baudrate: int = 9600

    # ---------------------- Connection management ----------------------
    def list_ports(self) -> List[dict]:
        ports = serial.tools.list_ports.comports()
        return [
            {
                "device": p.device,
                "name": getattr(p, "name", None),
                "description": getattr(p, "description", None),
                "hwid": getattr(p, "hwid", None),
                "manufacturer": getattr(p, "manufacturer", None),
                "serial_number": getattr(p, "serial_number", None),
                "location": getattr(p, "location", None),
                "vid": getattr(p, "vid", None),
                "pid": getattr(p, "pid", None),
            }
            for p in ports
        ]

    def connect(self, port: str, baudrate: int = 9600, timeout: float = 2.0) -> Tuple[bool, str]:
        with self._lock:
            if self._ser and self._ser.is_open:
                return True, f"Already connected to {self._port}"
            try:
                ser = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)
                # Give the Arduino time to reset after opening serial
                time.sleep(2)
                self._ser = ser
                self._port = port
                self._baudrate = baudrate
                return True, f"Connected to {port} at {baudrate}"
            except Exception as e:
                self._ser = None
                self._port = None
                return False, f"Connection failed: {e}"

    def disconnect(self) -> Tuple[bool, str]:
        with self._lock:
            if self._ser:
                success = True
                prev_port = self._port
                try:
                    self._ser.close()
                finally:
                    self._ser = None
                    self._port = None
                return success, f"Disconnected from {prev_port}"
            return True, "Not connected"

    def status(self) -> dict:
        with self._lock:
            return {
                "connected": bool(self._ser and self._ser.is_open),
                "port": self._port,
                "baudrate": self._baudrate,
            }

    # ---------------------- Helpers ----------------------
    def _write_line(self, s: str) -> None:
        assert self._ser is not None
        self._ser.write((s + "\n").encode("utf-8"))

    def _read_line(self, timeout: float) -> str:
        assert self._ser is not None
        self._ser.timeout = timeout
        line = self._ser.readline()
        return line.decode("utf-8", errors="ignore").strip()
    
    def _save_last_message(self, message):
        """Met à jour le dernier message et l'écrit dans le fichier."""
        with self.message_lock:
            self.last_message = message
            try:
                with open(STATUS_FILE_PATH, 'w', encoding='utf-8') as f:
                    # Ajoute un timestamp pour la traçabilité
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"[{timestamp}] {message}")
            except IOError as e:
                print(f"AVERTISSEMENT: Impossible d'écrire dans le fichier de statut: {e}")

    # ---------------------- Enrollment & Verification ----------------------
    def enroll_fingerprint(
        self,
        entity_id: int,
        max_retries: int = 3,
        per_try_timeout: float = 20.0,
    ) -> Tuple[bool, str]:
        """Enroll a fingerprint for a given ID using E + I:<id> sequence.
        Expects 'ENREGISTREMENT: SUCCES' from device.
        """
        with self._lock:
            if not (self._ser and self._ser.is_open):
                return False, "Arduino not connected"

            self._ser.reset_input_buffer()
            last_msg = ""
            for attempt in range(1, max_retries + 1):
                try:
                    # Enter enrollment mode and set ID
                    self._write_line("E")
                    # read ack lines quickly (non-blocking-ish)
                    _ = self._read_line(timeout=1.0)
                    self._write_line(f"I:{int(entity_id)}")
                    _ = self._read_line(timeout=1.0)

                    # Wait for enrollment result
                    # Device will emit ENREGISTREMENT: EN_COURS, then SUCCES or ECHEC/ABANDONNE
                    start = time.time()
                    while time.time() - start < per_try_timeout:
                        text = (self._read_line(timeout=2.0) or "").upper()
                        print(f"Enroll attempt {attempt}, received: {text}")
                        if not text:
                            continue
                        if "ENREGISTREMENT: SUCCES" in text:
                            return True, f"Enroll success on attempt {attempt}"
                        if "ENREGISTREMENT: ECHEC" in text:
                            last_msg = "ECHEC"
                            break
                        if "ENREGISTREMENT: ABANDONNE" in text:
                            return False, "Enroll cancelled"
                        # ignore other INFO/ACK lines
                    # retry if not successful
                except Exception as e:
                    last_msg = f"Error: {e}"
            return False, f"Enroll failed after {max_retries} attempts ({last_msg})"

    def verify_fingerprint(
        self,
        expected_id: Optional[int] = None,
        per_try_timeout: float = 3.0,
        max_polls: int = 10,
    ) -> Tuple[bool, str, Optional[int]]:
        """Verify by switching to V mode and polling for VERIFICATION result.
        Returns (success, message, matched_id). If expected_id is set, success is True only if matched_id == expected_id.
        """
        with self._lock:
            if not (self._ser and self._ser.is_open):
                return False, "Arduino not connected", None

            self._ser.reset_input_buffer()
            # Enter verify mode
            self._write_line("V")
            _ = self._read_line(timeout=1.0)

            polls = 0
            last_msg = ""
            while polls < max_polls:
                polls += 1
                text = (self._read_line(timeout=per_try_timeout) or "").upper()
                if not text:
                    continue
                if text.startswith("VERIFICATION: SUCCES"):
                    # Attempt to parse ID
                    matched_id = None
                    # find trailing number
                    for tok in text.split():
                        if tok.isdigit():
                            matched_id = int(tok)
                    # If expected specified, compare
                    if expected_id is None or (matched_id == expected_id):
                        return True, "Verification success", matched_id
                    else:
                        return False, f"Verification matched ID {matched_id}, expected {expected_id}", matched_id
                if "VERIFICATION: ECHEC" in text:
                    last_msg = "ECHEC"
                    # keep polling for next attempt
                    continue
                # ignore other lines
            return False, f"Verification timeout ({last_msg})", None

    def verify_fingerprint_stream(
        self,
        expected_id: Optional[int] = None,
        per_try_timeout: float = 3.0,
        max_polls: int = 0,
    ) -> Iterator[Dict]:
        """
        Streaming generator for verification.
        Yields dict events while polling the device. Events:
          - {"event":"info","message":...}
          - {"event":"line","raw": "..."}           # raw line received
          - {"event":"attempt_failed","message":...}
          - {"event":"result","success":bool,"matched_id":int|None,"message":...}
          - {"event":"timeout","message":...}
        If max_polls == 0, will poll until device returns a definitive result or timeout occurs per read.
        NOTE: This holds the serial lock for the duration of the generator to avoid concurrent access.
        """
        with self._lock:
            if not (self._ser and self._ser.is_open):
                yield {"event": "error", "message": "Arduino not connected"}
                return

            self._ser.reset_input_buffer()
            # Enter verify mode
            self._write_line("V")
            _ = self._read_line(timeout=1.0)

            polls = 0
            last_msg = ""
            try:
                while True:
                    if max_polls and polls >= max_polls:
                        yield {"event": "timeout", "message": f"Verification timeout ({last_msg})"}
                        return

                    polls += 1
                    text = (self._read_line(timeout=per_try_timeout) or "").strip()
                    if not text:
                        # keep-alive / heartbeat so caller knows we're still alive
                        yield {"event": "keepalive", "poll": polls}
                        continue

                    # yield raw line for client to decide
                    yield {"event": "line", "raw": text}

                    up = text.upper()
                    if up.startswith("VERIFICATION: SUCCES"):
                        matched_id = None
                        for tok in text.split():
                            if tok.isdigit():
                                matched_id = int(tok)
                        ok = (expected_id is None) or (matched_id == expected_id)
                        yield {
                            "event": "result",
                            "success": ok,
                            "matched_id": matched_id,
                            "message": "Verification success" if ok else f"Matched ID {matched_id}, expected {expected_id}",
                        }
                        return

                    if "VERIFICATION: ECHEC" in up:
                        last_msg = "ECHEC"
                        yield {"event": "attempt_failed", "message": text}
                        # continue polling
                        continue

                    # Other messages (INFO/ACK) forwarded
                    yield {"event": "info", "message": text}
            finally:
                # ensure we exit cleanly; nothing special to do here
                pass

    # Backward-compatible wrapper used by existing services for registration
    def capture_fingerprint(
        self,
        entity: str,
        entity_id: int,
        max_retries: int = 3,
        per_try_timeout: float = 20.0,
    ) -> Tuple[bool, str]:
        return self.enroll_fingerprint(entity_id=entity_id, max_retries=max_retries, per_try_timeout=per_try_timeout)


arduino_manager = ArduinoManager()
