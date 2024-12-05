import Adafruit_DHT
import requests
import time

# Specificera sensortyp och GPIO-pin
DHT_SENSOR = Adafruit_DHT.DHT11
DHT_PIN = 4  # Använd GPIO4 (pin nummer kan variera beroende på hur du anslutit)

# URL till ditt Flask API
API_URL = "http://<DIN_SERVER_IP>:5001/api/data"  # Ändra till IP-adressen för datorn som kör ditt API

# Intervall för hur ofta data skickas (30 sekunder)
INTERVAL = 30

# Funktionen för att samla in och skicka data
def send_data_to_api():
    while True:
        try:
            # Läs temperatur och luftfuktighet från DHT11-sensorn
            humidity, temperature = Adafruit_DHT.read(DHT_SENSOR, DHT_PIN)
            
            if humidity is not None and temperature is not None:
                print(f"Temperatur: {temperature:.2f}°C, Luftfuktighet: {humidity:.2f}%")

                # Data att skicka till API:t
                payload = {
                    "temperature": temperature,
                    "humidity": humidity
                }

                # Skicka POST-request till API:t
                response = requests.post(API_URL, json=payload)
                
                if response.status_code == 201:
                    print("Data skickad och inskriven i databasen.")
                else:
                    print(f"Fel vid skickning av data: {response.status_code}, {response.text}")

            else:
                print("Kunde inte läsa från DHT-sensorn.")

            # Vänta i 30 sekunder innan nästa mätning
            time.sleep(INTERVAL)

        except Exception as e:
            print(f"Ett oväntat fel inträffade: {e}")

if __name__ == "__main__":
    send_data_to_api()
