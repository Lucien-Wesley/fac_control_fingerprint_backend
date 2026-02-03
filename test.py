import serial

ser = serial.Serial("COM4", 9600, timeout=1)
print("Bluetooth ouvert")

while True:
    if ser.in_waiting:
        print(ser.readline().decode(errors="ignore").strip())
