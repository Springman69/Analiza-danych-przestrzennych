# Sprawozdanie – GeoPandas i Rasterio

## Część A – GeoPandas

### A2. Wczytanie danych

Wczytałem `pm25_sensors.csv` pandasem: 145 wierszy, 5 kolumn. W danych jest 5 duplikatów, 3 braki w `lat`, 4 w `lon` i wartości -999 w `pm25`. Minimum `lat` wynosi 17,87, bo w trzech wierszach lat i lon są zamienione.

![](screeny/a2_wczytanie.png)
![](screeny/a2_describe.png)

### A3. Czyszczenie

Usunąłem duplikaty i wiersze bez współrzędnych, naprawiłem zamienione lat/lon i usunąłem -999. Zostało 130 wierszy.

![](screeny/a3_czyszczenie.png)

### A4. GeoDataFrame

Z tabeli zrobiłem punkty w EPSG:4326. Wszystkie leżą w Opolu.

![](screeny/a4_geodataframe.png)

### A5. Układy współrzędnych

W EPSG:2180 odległość między dwoma pierwszymi czujnikami wychodzi 4906 m. Na odcinku Gdańsk–Zakopane EPSG:2180 myli się o -0,07%, a EPSG:3857 o +62%.

![](screeny/a5_odleglosc.png)
![](screeny/a5_uklady.png)

### A6. Dzielnice

Miasto ma 29 dzielnic i 148,8 km² powierzchni. Największe są Czarnowąsy (14,1 km²), najmniejsze Borki (0,66 km²).

![](screeny/a6_powierzchnie.png)
![](screeny/a6_mapa.png)

### A7. Złączenie przestrzenne

Wszystkie 130 czujników zostało przypisanych do dzielnic, 3 dzielnice nie mają żadnego czujnika. Wśród dzielnic z co najmniej 3 czujnikami najgorsze powietrze mają Stare Miasto (29,6 µg/m³), Śródmieście (26,8) i Zaodrze (22,5).

![](screeny/a7_ranking.png)
![](screeny/a7_kartogram.png)

### A8. Bufory wokół szkół

11 z 19 szkół ma czujnik w promieniu 500 m. Średnie PM2.5 przy szkołach wynosi 22,3 µg/m³, a bufory pokrywają 9,5% miasta.

![](screeny/a8_szkoly.png)
![](screeny/a8_pokrycie.png)
![](screeny/a8_bufory.png)

### A9. Zapis

Wyniki zapisałem do `pm25.gpkg` (dwie warstwy) i `pm25_districts.geojson`.

![](screeny/a9_zapis.png)
![](screeny/a9_kontrola.png)

## Część B Rasterio

### B2. Metadane

Rastry mają 1995 × 1426 px, typ float32, układ EPSG:4326 i brak nodata. Piksel ma ok. 6,3 × 6,3 m.

![](screeny/b2_metadane.png)
![](screeny/b2_piksel.png)

### B3. Piksel ↔ współrzędne

Rynek wypada w pikselu (671, 960), NDVI ma tam wartość 0,07.

![](screeny/b3_piksel_wsp.png)

### B4. Pasma i histogramy

![](screeny/b4_pasma.png)

### B5. Reprojekcja

Oba pasma przeliczyłem na EPSG:2180 z pikselem 10 m.

![](screeny/b5_reprojekcja.png)

### B6. NDVI

Średnie NDVI dla całej sceny wynosi 0,49.

![](screeny/b6_ndvi_stat.png)
![](screeny/b6_ndvi_mapa.png)

### B7. Klasyfikacja

![](screeny/b7_klasy.png)

### B8. NDVI w dzielnicach

Zdjęcie nie obejmuje północy miasta, więc w rankingu są tylko dzielnice pokryte w co najmniej 90%. Najwięcej zieleni ma Nadodrze (0,66), najmniej Stare Miasto (0,36).

![](screeny/b8_ranking.png)
![](screeny/b8_mapa.png)

### B9. Zapis

![](screeny/b9_zapis.png)

## Wnioski

Najgorsze powietrze i najmniej zieleni są w centrum (Stare Miasto, Śródmieście), a najwięcej zieleni ma Nadodrze. Odległości, powierzchnie i bufory trzeba liczyć w układzie metrycznym (EPSG:2180), a dane przed analizą trzeba dokładnie przejrzeć i oczyścić.
