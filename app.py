from flask import Flask, request, jsonify
import pyodbc
import logging
import time
from datetime import datetime
import pytz
from config import Config

# Dash imports
import dash
from dash import dcc, html
import plotly.graph_objs as go
import pandas as pd
from sqlalchemy import create_engine

# Flask-applikationen
app = Flask(__name__)
app.config.from_object(Config)

# Definiera Stockholms tidszon
stockholm_tz = pytz.timezone('Europe/Stockholm')
utc_tz = pytz.utc

# Funktion för att hämta databasanslutningen med pyodbc
def get_db_connection():
    retries = 3
    for attempt in range(retries):
        try:
            logging.info(f"Försöker ansluta till databasen (försök {attempt + 1} av {retries})")
            conn = pyodbc.connect(
                f'DRIVER={Config.SQL_DRIVER};'
                f'SERVER={Config.SQL_SERVER};'
                f'PORT=1433;DATABASE={Config.SQL_DATABASE};'
                f'UID={Config.SQL_USERNAME};PWD={Config.SQL_PASSWORD}'
            )
            logging.info("Anslutning till databasen lyckades")
            return conn
        except pyodbc.InterfaceError as e:
            logging.error(f"InterfaceError vid anslutning till databasen: {e}")
        except pyodbc.OperationalError as e:
            logging.error(f"OperationalError vid anslutning till databasen: {e}")
        except pyodbc.Error as e:
            logging.error(f"Allmänt fel vid anslutning till databasen: {e}")
        except Exception as e:
            logging.error(f"Oväntat fel vid anslutning till databasen: {e}")

        # Vänta innan nästa försök
        time.sleep(2)

    logging.error("Misslyckades att ansluta till databasen efter flera försök.")
    return None

# API-endpoint för att ta emot data
@app.route('/api/data', methods=['POST'])
def receive_data():
    # Ta emot JSON-data från Raspberry Pi
    data = request.get_json()

    try:
        temperature = float(data.get('temperature'))
        humidity = float(data.get('humidity'))
    except (ValueError, TypeError):
        return jsonify({"error": "Temperatur eller luftfuktighet är i fel format"}), 400

    if temperature is None or humidity is None:
        return jsonify({"error": "Temperatur eller luftfuktighet saknas"}), 400

    # Hämta nuvarande tid i Stockholm-tidszon och konvertera till UTC för att spara i databasen
    current_time = datetime.now(stockholm_tz)
    current_time_utc = current_time.astimezone(utc_tz)

    # Anslut till databasen och lägg till datan
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Kunde inte ansluta till databasen"}), 500

    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO SensorData (Temperature, Humidity, Timestamp)
            VALUES (?, ?, ?)
        ''', (temperature, humidity, current_time_utc))
        conn.commit()
        logging.info(f"Data inskriven i databasen: Temperatur={temperature}, Luftfuktighet={humidity}, Tidstämpel={current_time_utc}")
        return jsonify({"message": "Data inskriven i databasen"}), 201
    except pyodbc.Error as e:
        logging.error(f"Fel vid inskrivning till databasen: {e}")
        return jsonify({"error": "Fel vid inskrivning till databasen"}), 500
    finally:
        cursor.close()
        conn.close()

# Funktion för att hämta data från databasen med SQLAlchemy
def get_data_from_db():
    try:
        # Skapa en SQLAlchemy engine
        engine = create_engine(
            f"mssql+pyodbc://{Config.SQL_USERNAME}:{Config.SQL_PASSWORD}@{Config.SQL_SERVER}:1433/{Config.SQL_DATABASE}?driver=ODBC+Driver+18+for+SQL+Server"
        )

        # Hämta data till en Pandas DataFrame och sortera efter Timestamp i fallande ordning
        df = pd.read_sql("SELECT * FROM SensorData ORDER BY Timestamp DESC", engine)
        
        # Konvertera Timestamp från UTC till Stockholm tidszon för presentation
        df['Timestamp'] = pd.to_datetime(df['Timestamp']).dt.tz_localize('UTC').dt.tz_convert('Europe/Stockholm')

        return df
    except Exception as e:
        logging.error(f"Fel vid hämtning av data från databasen: {e}")
        return pd.DataFrame()  # Returnerar en tom dataframe om det blir fel

# Dash-applikation för visualisering
dash_app = dash.Dash(__name__, server=app, url_base_pathname='/dashboard/')

# Definiera layouten för Dash-applikationen
dash_app.layout = html.Div(children=[
    html.H1(children='Luftfuktighet och Temperaturdata från Sensorer', style={'textAlign': 'center', 'fontSize': 30}),

    dcc.Graph(id='temperature-humidity-graph'),

    html.Div(children=[
        html.Div(id='live-temperature', style={
            'display': 'inline-block',
            'padding': '20px',
            'borderRadius': '10px',
            'backgroundColor': '#2b2b2b',
            'margin': '10px',
            'boxShadow': '2px 2px 5px rgba(0, 0, 0, 0.1)',
            'fontSize': '28px',
            'color': '#ff5733',
            'textAlign': 'center'
        }),
        html.Div(id='live-humidity', style={
            'display': 'inline-block',
            'padding': '20px',
            'borderRadius': '10px',
            'backgroundColor': '#2b2b2b',
            'margin': '10px',
            'boxShadow': '2px 2px 5px rgba(0, 0, 0, 0.1)',
            'fontSize': '28px',
            'color': '#3498db',
            'textAlign': 'center'
        }),
    ], style={'textAlign': 'center', 'marginTop': '20px'}),

    # Interval komponent för att uppdatera data
    dcc.Interval(
        id='interval-component',
        interval=30 * 1000,  # Uppdatera varje 30 sekunder (30 000 millisekunder)
        n_intervals=0
    )
])

# Callback för att uppdatera grafen och live-värdena
@dash_app.callback(
    [dash.dependencies.Output('temperature-humidity-graph', 'figure'),
     dash.dependencies.Output('live-temperature', 'children'),
     dash.dependencies.Output('live-humidity', 'children')],
    [dash.dependencies.Input('interval-component', 'n_intervals')]
)
def update_graph(n_intervals):
    df = get_data_from_db()

    if df.empty:
        return {}, "Inga data tillgängliga", "Inga data tillgängliga"

    # Skapa grafen med rätt kolumnnamn från databasen
    figure = {
        'data': [
            go.Scatter(
                x=df['Timestamp'],
                y=df['Temperature'],
                mode='lines+markers',
                name='Temperature (°C)',
                line=dict(color='orange', shape='linear')
            ),
            go.Scatter(
                x=df['Timestamp'],
                y=df['Humidity'],
                mode='lines+markers',
                name='Humidity (%)',
                line=dict(color='blue', shape='linear')
            )
        ],
        'layout': go.Layout(
            title='Sensor Data över Tid',
            xaxis={'title': 'Tid'},
            yaxis={'title': 'Värde'},
            template='plotly_dark',
            hovermode='closest'
        )
    }

    # Logg för att se vilket värde som hämtas
    logging.info(f"Senaste temperatur: {df['Temperature'].iloc[0]}, Senaste luftfuktighet: {df['Humidity'].iloc[0]}")

    # Senaste temperatur och luftfuktighet
    latest_temperature = df['Temperature'].iloc[0]
    latest_humidity = df['Humidity'].iloc[0]

    # Gör texten mer tilltalande
    live_temperature_text = f"Live Temperatur: {latest_temperature:.2f}°C"
    live_humidity_text = f"Live Luftfuktighet: {latest_humidity:.2f}%"

    return figure, live_temperature_text, live_humidity_text

# Starta Flask-applikationen
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)  # Använd port 5001 och kör i debug-läge
