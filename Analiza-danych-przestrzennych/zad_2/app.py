"""Opole: PM2.5 (GeoPandas) i NDVI (Rasterio). Uruchom: streamlit run app.py"""
from pathlib import Path

import folium
import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import streamlit as st
from rasterio.io import MemoryFile
from rasterio.mask import mask
from rasterio.warp import Resampling, calculate_default_transform, reproject
from streamlit_folium import st_folium

DATA = Path(__file__).parent / "dane"
CRS_M = "EPSG:2180"
RES = 10

st.set_page_config(page_title="Opole: PM2.5 i NDVI", page_icon="🗺️", layout="wide")


# ---------- dane wektorowe ----------
@st.cache_data
def load_vectors():
    raw = pd.read_csv(DATA / "pm25_sensors.csv", parse_dates=["measured_at"])
    df = raw.drop_duplicates().dropna(subset=["lat", "lon"]).copy()
    sw = df["lat"].between(14, 24.5) & df["lon"].between(49, 55)
    df.loc[sw, ["lat", "lon"]] = df.loc[sw, ["lon", "lat"]].to_numpy()
    df = df[df["pm25"] >= 0].reset_index(drop=True)
    report = {"wiersze wejściowe": len(raw), "zamienione lat/lon": int(sw.sum()), "czyste wiersze": len(df)}

    sensors = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df["lon"], df["lat"]), crs="EPSG:4326").to_crs(CRS_M)
    districts = gpd.read_file(DATA / "opole_districts.geojson").to_crs(CRS_M)
    districts["area_km2"] = districts.area / 1e6
    schools = gpd.read_file(DATA / "opole_schools.geojson").to_crs(CRS_M)
    return sensors, districts, schools, report


# ---------- dane rastrowe ----------
@st.cache_data
def load_ndvi():
    def to_grid(path, transform, w, h):
        out = np.full((h, w), np.nan, dtype="float32")
        with rasterio.open(path) as src:
            reproject(rasterio.band(src, 1), out, src_transform=src.transform, src_crs=src.crs,
                      dst_transform=transform, dst_crs=CRS_M, dst_nodata=np.nan,
                      resampling=Resampling.bilinear)
        return out

    b04, b08 = DATA / "S2_L2A_2026-10-06_B04.tiff", DATA / "S2_L2A_2026-10-06_B08.tiff"
    with rasterio.open(b04) as src:
        transform, w, h = calculate_default_transform(src.crs, CRS_M, src.width, src.height,
                                                      *src.bounds, resolution=RES)
    red, nir = to_grid(b04, transform, w, h), to_grid(b08, transform, w, h)
    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi = (nir - red) / (nir + red)
    return ndvi, transform


@st.cache_data
def zonal_ndvi(_districts, threshold):
    ndvi, transform = load_ndvi()
    h, w = ndvi.shape
    profile = dict(driver="GTiff", height=h, width=w, count=1, dtype="float32",
                   crs=CRS_M, transform=transform, nodata=np.nan)
    rows = []
    with MemoryFile() as mem, mem.open(**profile) as ds:
        ds.write(ndvi, 1)
        for _, d in _districts.iterrows():
            try:
                arr, _ = mask(ds, [d.geometry], crop=True, nodata=np.nan, filled=True)
                v = arr[0][~np.isnan(arr[0])]
            except ValueError:
                v = np.array([], dtype="float32")
            rows.append({"name": d["name"],
                         "ndvi_mean": float(v.mean()) if v.size else np.nan,
                         "green_share": float((v > threshold).mean()) if v.size else np.nan,
                         "coverage": min(v.size * RES * RES / d.geometry.area, 1.0)})
    return pd.DataFrame(rows)


def show_map(gdf, column, cmap, caption, extra=None):
    m = gdf.to_crs("EPSG:4326").explore(
        column=column, cmap=cmap, legend=True, legend_kwds={"caption": caption},
        missing_kwds={"color": "lightgray", "label": "brak danych"},
        tooltip=["name", column], style_kwds={"fillOpacity": 0.7})
    if extra is not None:
        extra(m)
    folium.LayerControl().add_to(m)
    st_folium(m, height=520, use_container_width=True, returned_objects=[])


sensors, districts, schools, report = load_vectors()

st.sidebar.title("🗺️ Opole")
page = st.sidebar.radio("Analiza", ["💨 PM2.5 (GeoPandas)", "🌿 NDVI (Rasterio)"])

if page.startswith("💨"):
    st.title("Które dzielnice mają najgorsze powietrze?")
    min_n = st.sidebar.slider("Min. liczba czujników w dzielnicy", 1, 5, 3)
    radius = st.sidebar.slider("Promień wokół szkoły [m]", 100, 2000, 500, step=100)

    c1, c2, c3 = st.columns(3)
    c1.metric("Wiersze w CSV", report["wiersze wejściowe"])
    c2.metric("Naprawione lat/lon", report["zamienione lat/lon"])
    c3.metric("Czujniki po czyszczeniu", report["czyste wiersze"])

    joined = gpd.sjoin(sensors, districts[["name", "geometry"]], how="left", predicate="within")
    stats = joined.groupby("name").agg(pm25_mean=("pm25", "mean"), sensor_count=("pm25", "size")).round(1)
    summary = districts.merge(stats, on="name", how="left")
    summary.loc[summary["sensor_count"].fillna(0) < min_n, "pm25_mean"] = np.nan

    left, right = st.columns([3, 2])
    with left:
        show_map(summary, "pm25_mean", "Oranges", "średnie PM2.5 [µg/m³]",
                 extra=lambda m: sensors.to_crs("EPSG:4326").explore(
                     m=m, color="black", marker_kwds={"radius": 3}, name="czujniki"))
    with right:
        st.subheader(f"Ranking (≥ {min_n} czujniki)")
        st.dataframe(summary.dropna(subset=["pm25_mean"])
                     .sort_values("pm25_mean", ascending=False)[["name", "pm25_mean", "sensor_count"]],
                     hide_index=True, width="stretch")

    st.header(f"Szkoły: czujniki w promieniu {radius} m")
    buffers = schools.copy()
    buffers["geometry"] = schools.buffer(radius)
    near = gpd.sjoin(sensors, buffers[["name", "geometry"]], predicate="within")
    city = districts.union_all()
    coverage = buffers.union_all().intersection(city).area / city.area
    c1, c2, c3 = st.columns(3)
    c1.metric("Szkoły z czujnikiem", f"{near['name'].nunique()} / {len(schools)}")
    c2.metric("Średnie PM2.5 przy szkołach", f"{near['pm25'].mean():.1f} µg/m³" if len(near) else "—")
    c3.metric("Pokrycie miasta buforami", f"{coverage:.1%}")
    st.dataframe(near.groupby("name").agg(pm25_mean=("pm25", "mean"), sensors=("pm25", "size")).round(1)
                 .sort_values("pm25_mean", ascending=False), width="stretch")

else:
    st.title("Gdzie w Opolu jest najwięcej zieleni?")
    st.caption("Sentinel-2 L2A, 6.10.2026 · NDVI = (B08 − B04) / (B08 + B04) · siatka 10 m w EPSG:2180")
    thr = st.sidebar.slider("Próg „gęstej zieleni” (NDVI >)", 0.2, 0.8, 0.5, step=0.05)
    min_cov = st.sidebar.slider("Min. pokrycie dzielnicy sceną", 0.0, 1.0, 0.9, step=0.05)

    ndvi, _ = load_ndvi()
    valid = ndvi[~np.isnan(ndvi)]
    px_ha = RES * RES / 10_000
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Średnie NDVI sceny", f"{valid.mean():.2f}")
    c2.metric("Woda (NDVI < 0)", f"{(valid < 0).sum() * px_ha:,.0f} ha")
    c3.metric(f"Gęsta zieleń (> {thr})", f"{(valid > thr).sum() * px_ha:,.0f} ha")
    c4.metric("Udział gęstej zieleni", f"{(valid > thr).mean():.1%}")

    zonal = zonal_ndvi(districts, thr)
    gdf = districts.merge(zonal, on="name")
    gdf.loc[gdf["coverage"] < min_cov, ["ndvi_mean", "green_share"]] = np.nan

    left, right = st.columns([3, 2])
    with left:
        show_map(gdf, "ndvi_mean", "RdYlGn", "średnie NDVI")
    with right:
        st.subheader(f"Ranking (pokrycie ≥ {min_cov:.0%})")
        st.dataframe(gdf.dropna(subset=["ndvi_mean"]).sort_values("ndvi_mean", ascending=False)
                     [["name", "ndvi_mean", "green_share", "coverage"]].round(3),
                     hide_index=True, width="stretch")
    st.info("Scena nie pokrywa północy miasta. Dzielnice z małym pokryciem są wyszarzone, "
            "bo ich średnia pochodzi z niereprezentatywnego skrawka.")
