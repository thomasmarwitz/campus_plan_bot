# Dataset creation

## Data fetching

The data was fetched from [this website](https://www.kit.edu/campusplan/)'s sources, specifically, the `data_de.js` file. The initial data only contains names, a category (building, lecture hall, etc.) and a location (latitude and longitude).

## Data enrichment

We use reverse geocoding ([Nomatim](https://nominatim.org/release-docs/develop/api/Reverse/)), for the result, check [this example](https://nominatim.openstreetmap.org/reverse?format=geojson&lat=49.01137&lon=8.41882). Among the address, we get the `osmId` and `osmType`, which we can use to query further values. This is done with the Nominatim details API, which is documented here: [Nominatim details](https://nominatim.org/release-docs/develop/api/Details/). The process is described in this article: [Getting started with OpenStreetMap Nominatim API](https://medium.com/@adri.espejo/getting-started-with-openstreetmap-nominatim-api-e0da5a95fc8a), an example result can be found [here](https://nominatim.openstreetmap.org/details?osmtype=W&osmid=937998754&format=json).


### Implementation plan

- [x] Raw data is available
- [x] Following per data point, save all raw data in a json file per data point
  - Reverse geocode the data
  - Query the Nominatim details API for each data point
- [x] Merge the data, using selected fields (adjustable in jupyter notebook)
  - [ ] TBD: probably keep raw object around