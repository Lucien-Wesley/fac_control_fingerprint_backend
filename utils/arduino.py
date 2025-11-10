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
    """
    Gère la connexion série Arduino et la lecture en arrière-plan.
    """
    _instance = None
    _is_running = False

    def __new__(cls, *args, **kwargs):
        """Implémente le pattern Singleton."""
        if cls._instance is None:
            cls._instance = super(ArduinoManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.last_message = "Initialisation en cours..."
        self.message_lock = threading.Lock()
        self._ser: Optional[serial.Serial] = None
        self._port: Optional[str] = None
        self._baudrate: int = 9600

        self.reader_thread = None
        self._initialized = True
        self._is_running = False

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
                # Démarrer le thread de lecture après la connexion
                self.start_reader()
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
    def _serial_reader(self):
        """Fonction du thread: lit en continu le port série."""
        print("INFO: Thread de lecture série démarré.")
        while self._is_running and self._ser:
            try:
                # Lecture ligne par ligne non bloquante
                if self._ser.in_waiting > 0:
                    # Le .readline() bloquerait si le timeout était non-nul. 
                    # Avec timeout=0, il retourne immédiatement. On s'assure qu'il y a des données.
                    line = self._ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        print(f"ARDUINO -> {line}")
                        self._save_last_message(f"{line}")
                        
                else:
                    time.sleep(0.05) # Petite pause pour libérer le CPU
            except serial.SerialTimeoutException:
                pass # Géré par in_waiting, mais bonne pratique de l'inclure
            except serial.SerialException as e:
                print(f"ERREUR SÉRIE (lecture): {e}")
                self._save_last_message(f"ERREUR SÉRIE: {e}")
                self._ser = None # Déconnecter en cas d'erreur grave
                self._is_running = False
            except Exception as e:
                print(f"ERREUR INCONNUE (lecture): {e}")
                time.sleep(1)

        print("INFO: Thread de lecture série arrêté.")


    def start_reader(self):
        """Démarre le thread de lecture."""
        if self._ser and not self._is_running:
            self._is_running = True
            self.reader_thread = threading.Thread(target=self._serial_reader, daemon=True)
            self.reader_thread.start()

    def send_command(self, command):
        """Envoie une commande à l'Arduino."""
        if not self._ser:
            # Mode sans Arduino, renvoyer une erreur explicite
            error_msg = f"ERREUR: Non connecté au port série (sélectionné ou par défaut)."
            self._save_last_message(error_msg)
            return False, error_msg

        try:
            # Les commandes de l'Arduino attendent un \n
            self._ser.write((command + '\n').encode('utf-8'))
            print(f"PC -> {command}")
            return True, f"Commande '{command}' envoyée."
        except serial.SerialException as e:
            self._save_last_message(f"ERREUR SÉRIE (écriture): {e}")
            print(f"ERREUR SÉRIE (écriture): {e}")
            self._ser = None
            self._is_running = False
            return False, f"Erreur lors de l'envoi de la commande: {e}"
        except Exception as e:
            return False, f"Erreur inattendue lors de l'envoi: {e}"

    def get_last_message(self):
        """Récupère le dernier message lu."""
        with self.message_lock:
            return self.last_message

    def shutdown(self):
        """Arrête le thread et ferme la connexion série."""
        if self._is_running:
            self._is_running = False
            if self.reader_thread and self.reader_thread.is_alive():
                self.reader_thread.join(timeout=2)
        if self._ser:
            self._ser.close()
            print("INFO: Connexion série fermée.")


arduino_manager = ArduinoManager()
