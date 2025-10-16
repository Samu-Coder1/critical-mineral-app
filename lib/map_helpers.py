import folium
from folium.plugins import MarkerCluster
from branca.element import Template, MacroElement

def build_map_html(sites_full):
    """Builds a Folium map for sites_full (DataFrame with SiteName, CountryName, MineralName, Production_tonnes, Latitude, Longitude).
    Returns rendered HTML string for embedding."""
    m = folium.Map(location=[-10, 25], zoom_start=3)

    folium.TileLayer(
        tiles='https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
        attr='&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>',
        name='Road Map'
    ).add_to(m)

    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community',
        name='Satellite'
    ).add_to(m)

    folium.TileLayer(
        tiles='https://{s}.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}.png',
        attr='&copy; <a href="https://carto.com/">CARTO</a>',
        name='Satellite Labels (English)',
        overlay=True,
        control=True
    ).add_to(m)

    cluster = MarkerCluster(name='Sites').add_to(m)
    for _, row in sites_full.iterrows():
        popup = (
            f"<b>{row['SiteName']}</b><br>"
            f"Country: {row['CountryName']}<br>"
            f"Mineral: {row['MineralName']}<br>"
            f"Production: {row['Production_tonnes']:,.0f} tonnes"
        )
        folium.Marker(
            [row['Latitude'], row['Longitude']],
            popup=folium.Popup(popup, max_width=300),
            tooltip=row['SiteName']
        ).add_to(cluster)

    folium.LayerControl().add_to(m)

    legend_html = '''
    <div style="position: fixed; bottom: 50px; left: 10px; width: 210px; z-index:9999; font-size:12px;">
        <div style="background:white; padding:8px; border:1px solid #ccc;">
            <b>Map layers</b><br>
            - Road Map: labeled basemap (English)<br>
            - Satellite: imagery<br>
            - Satellite Labels: English place names (toggle on for labels)<br>
        </div>
    </div>
    '''
    tpl = Template(legend_html)
    macro = MacroElement()
    macro._template = tpl
    m.get_root().add_child(macro)

    return m._repr_html_()
