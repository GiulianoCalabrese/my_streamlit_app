import streamlit as st
# Base packages
import pandas as pd
import numpy as np
import datetime
import altair as alt
import matplotlib.pyplot as plt
# Plot interactive maps
import geopandas as gpd
from shapely import wkt
from bokeh.io import output_notebook, show, output_file
from bokeh.plotting import figure
from bokeh.models import GeoJSONDataSource, ColumnDataSource
import json
from bokeh.models import HoverTool
# Command to launch Ngrok: ./ngrok http 8501

########################################################################################
#LAUNCH APP!! put on the terminal the command : 
#streamlit run test.py
#########################################################################


st.header("COVID-19 au Sénégal 🇸🇳")
st.sidebar.markdown("*Dernière mise à jour: 02/04/2020*")
st.sidebar.markdown("---")
st.sidebar.header("Ressources utiles")
st.sidebar.markdown("Numéro d'urgence 1: **78 172 10 81**")
# I. Dataframe
df = pd.read_csv("https://raw.githubusercontent.com/maelfabien/COVID-19-Senegal/master/COVID_Senegal.csv", sep=";")
df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)
# II. Summary of the number of cases
st.markdown("---")
evol_cases = df[['Date', 'Positif', 'Negatif', 'Décédé', 'Guéri']].groupby("Date").sum().cumsum()
st.subheader("En bref")
total_positif = evol_cases.tail(1)['Positif'][0]
total_negatif = evol_cases.tail(1)['Negatif'][0]
total_decede = evol_cases.tail(1)['Décédé'][0]
total_geuri = evol_cases.tail(1)['Guéri'][0]
st.markdown("Nombre de malades: <span style='font-size:1.5em;'>%s</span>"%(total_positif - total_geuri), unsafe_allow_html=True)
st.markdown("Nombre de décès: <span style='font-size:1.5em;'>%s</span>"%(total_decede), unsafe_allow_html=True)
st.markdown("Nombre de guérisons: <span style='font-size:1.5em;'>%s</span>"%(total_geuri), unsafe_allow_html=True)
st.markdown("Pourcentage de guerison: <span style='font-size:1.5em;'>%s</span>"%(np.round(total_geuri / total_positif * 100, 1)), unsafe_allow_html=True)
st.markdown("Taux de croissance journalier lissé sur les 2 derniers jours: <span style='font-size:1.5em;'>%s</span>"%(np.round(pd.DataFrame(np.sqrt(evol_cases['Positif'].pct_change(periods=2)+1)-1).tail(1)['Positif'][0] * 100, 2)), unsafe_allow_html=True)
st.markdown("Nombre total de cas positifs: <span style='font-size:1.5em;'>%s</span>"%(total_positif), unsafe_allow_html=True)
st.markdown("Nombre de tests negatifs: <span style='font-size:1.5em;'>%s</span>"%(total_negatif), unsafe_allow_html=True)
st.markdown("Nombre de tests réalisés: <span style='font-size:1.5em;'>%s</span>"%(total_positif + total_negatif), unsafe_allow_html=True)
st.markdown("Pourcentage de tests positifs: <span style='font-size:1.5em;'>%s</span>"%(np.round(total_positif / (total_positif + total_negatif) * 100, 1)), unsafe_allow_html=True)
# III. Interactive map
st.markdown("---")#https://files.slack.com/files-pri/TBQ8Y1E2G-F05FUP579AP/download/challenges_2023_07_05_interactive_map.ipynb?origin_team=TBQ8Y1E2G
st.subheader("Carte des cas positifs")
shapefile = '03-Streamlit/app/ne_110m_admin_0_countries.shp'
#Read shapefile using Geopandas
#import os
#print(os.getcwd())
#print("\n")
gdf = gpd.read_file(shapefile)[['ADMIN', 'ADM0_A3', 'geometry']]
gdf.columns = ['country', 'country_code', 'geometry']
gdf = gdf[gdf['country']=="Senegal"]
grid_crs=gdf.crs
gdf_json = json.loads(gdf.to_json())
grid = json.dumps(gdf_json)
cities = pd.read_csv("city_coordinates.csv", index_col=0)
def find_lat(x):
    try:
        return float(cities[cities['Ville'] == x]['Latitude'])
    except TypeError:
        return None
def find_long(x):
    try:
        return float(cities[cities['Ville'] == x]['Longitude'])
    except TypeError:
        return None
summary = df[['Positif', 'Ville']].groupby("Ville").sum().reset_index()
summary['latitude'] = summary['Ville'].apply(lambda x: find_lat(x))
summary['longitude'] = summary['Ville'].apply(lambda x: find_long(x))
geosource = GeoJSONDataSource(geojson = grid)
pointsource = ColumnDataSource(summary)
hover = HoverTool(
    tooltips = [('Ville', '@Ville'), ('Nombre de cas positifs (au moins)', '@Positif')]
)
#Create figure object.
p = figure(height = 550 , width = 700, tools=[hover, 'pan', 'wheel_zoom'])
p.xgrid.grid_line_color = None
p.ygrid.grid_line_color = None
p.xaxis.visible = False
p.yaxis.visible = False
p.outline_line_color = None
patch = p.patches('xs','ys', source = geosource, fill_color = 'lightgrey',
          line_color = 'black', line_width = 0.25, fill_alpha = 1)
p.circle('longitude','latitude',source=pointsource, size=15)
st.bokeh_chart(p)
# IV. Evolution of the number of cases in Senegal
st.markdown("---")
st.subheader("Evolution du nombre de cas positifs au Sénégal")
st.write("La courbe 'Positif' représente l'ensemble des cas, et la courbe 'Actifs' élimine les cas guéris et représente le nombre de cas actifs.")
evol_cases['Actifs'] = evol_cases['Positif'] - evol_cases['Guéri']
ch0 = alt.Chart(evol_cases.reset_index()).transform_fold(
    ['Positif', 'Actifs'],
).mark_line(size=5, point=True).encode(
    x='Date:T',
    y='value:Q',
    color='key:N', 
    tooltip="value:Q"
).properties(height=400, width=700)
st.write(ch0)
# V. Source of infection
st.markdown("---")
st.subheader("Contamination")
st.write("Nous distinguon les cas importés (voyageurs en provenance de l'extérieur) des cas contact qui ont été en contact avec une personne malade. Les cas Communauté sont des cas dont les contacts directs ne peuvent être établis, et donc les plus dangereux.")
facteur = df[['Date', 'Facteur']].dropna()
#facteur['Count'] = 1
facteur["Imported"] = np.where(facteur["Facteur"] == "Importé", 1, 0)
facteur["Contact"] = np.where(facteur["Facteur"] == "Contact", 1, 0)
facteur["Communauté"] = np.where(facteur["Facteur"] == "Communauté", 1, 0)
st.write("Nombre total de cas importés: ", facteur["Facteur"].value_counts()[1])
st.write("Nombre total de cas contact: ", facteur["Facteur"].value_counts()[0])
st.write("Nombre total de cas communauté: ", facteur["Facteur"].value_counts()[2])
facteur["CumImported"] =  facteur["Imported"].cumsum()
facteur["CumContact"] =  facteur["Contact"].cumsum()
facteur["CumCommunauté"] =  facteur["Communauté"].cumsum()

ch0 = alt.Chart(facteur).transform_fold(
    ["CumImported" ,"CumContact", "CumCommunauté" ],
).mark_line(size=5).encode(
    x='Date:T',
    y='value:Q',
    color='key:N'
).properties(height=500, width=700)
st.altair_chart(ch0)
st.write("Les cas importés, ayant ensuite crée des cas contact, proviennent des pays suivants:")
ch3 = alt.Chart(df.dropna(subset=['Source/Voyage'])).mark_bar().encode(
    x = 'Source/Voyage:N',
    y=alt.Y('count()', title='Nombre de patients')
).properties(title="Provenance des malades", height=300, width=700)
st.write(ch3)
# VI. Insights about the population
st.markdown("---")
st.subheader("Population touchée")
st.write("Les chiffres présentés ci-dessous tiennent compte des publication du Ministère de la Santé et de l'Action Sociale. Certaines données sont manquantes, et nous n'affichons que les valeurs connues à ce jour.")
st.write("1. L'age moyen des patients est de ", np.mean(df['Age'].dropna()), " ans")
ch = alt.Chart(df).mark_bar().encode(
    x = 'Age:Q',
    y=alt.Y('count()', title='Nombre de patients')
).properties(title="Age des patients ", height=300, width=700)
st.write(ch)
st.write("2. La plupart des patients connus sont des hommes")
st.write(pd.DataFrame(df[['Homme', 'Femme']].dropna().sum()).transpose())
st.write("3. La plupart des cas sont concentrés à Dakar")
ch2 = alt.Chart(df.dropna(subset=['Ville'])).mark_bar().encode(
    x = 'Ville:N',
    y=alt.Y('count()', title='Nombre de patients')
).properties(title="Ville des cas", height=300, width=700)
st.write(ch2)
st.write("4. La plupart des personnes malades résident au Sénégal")
st.write(df['Resident Senegal'].dropna().value_counts())
st.write("5. Le temps d'hospitalisation moyen pour le moment est de : ", np.mean(df['Temps Hospitalisation (j)'].dropna()), " jours")


st.write("6. POUR ALLER PLUS LOIN Deploy your app with Streamlit Cloud")


#####################DEPLOY your app with steamlit Cloud##############################
"""

Streamlit also provide the possibility to deploy your application in their cloud. It is an extremely easy-to-use service that allows you to deploy the content from a GitHub repository.
4.1. Build the app. First of all create a directory to store the app.py file.

mkdir my_streamlit_app

Then put in the app.py file with the script of your app in the new directory. Finaly, create a requirements.txt file in the directory. This file lists all the packages and their versions that are needed to run the application.

## To create the requirements.txt file, first install pipreqs: pip install pipreqs
Then, go to the root of your app folder, and simply run:

pipreqs

You will now have a requirements.txt file in your repo.
4.2 Push your app on GitHub

You will need to have the content of your app in a Github repository.

First of all, init git at the root of your app folder and commit your files:

git init -b main
git add --all
git commit -m "my first commit"

Then, create a repository on GitHub : https://github.com/new and copy the ssh link of the repository.

Add this link to your local Git folder:

git remote add origin {remote repository ssh link}

Finally, push your commit.

git push origin main

5.2. Deployment with Streamlit Cloud

First, go to: https://streamlit.io/cloud and sign-up with your GitHub account. In your account clic on new app button, select your repository, the branch (main) and the name of the app script (app.py).
##Hint: if there are errors during deployement, read the error, generaly it is just a error with a packages, version, change the requirements.txt file, commit changes, push on GitHub and retry to deploy !
"""
