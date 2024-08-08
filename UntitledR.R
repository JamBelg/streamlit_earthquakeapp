library(shiny)
library(dotenv)
library(aws.s3)
library(DT)
library(plotly)
library(dplyr)
library(leaflet)
library(RColorBrewer)



# dotenv::load_dot_env(file=".env")
# AWS_ACCESS_KEY_ID = Sys.getenv("aws_access_key_id")
# AWS_SECRET_ACCESS_KEY = Sys.getenv("aws_secret_access_key")
# AWS_DEFAULT_REGION <- "us-east-1"
# Sys.setenv(
#   "AWS_ACCESS_KEY_ID" = AWS_ACCESS_KEY_ID,
#   "AWS_SECRET_ACCESS_KEY" = AWS_SECRET_ACCESS_KEY,
#   "AWS_DEFAULT_REGION" = AWS_DEFAULT_REGION
# )
# bucket_name <- "earthquakedb"
# s3_file <- "data_etl.csv"
# data <- s3read_using(FUN = read.csv, bucket = bucket_name, object = s3_file) %>%
#   mutate('Date UTC'=as.Date(paste0(Year, ' ', UTC_Time), format="%Y %b %d")) %>%
#   select('Date UTC', Location, Magnitude, Depth, Latitude, Longitude) %>%
#   filter(Magnitude>0)
# write.csv(data, 'data_offline.csv')
data <- read.csv('data_offline.csv', sep=',')


min(data$Latitude)
max(data$Latitude)

min(data$Longitude)
max(data$Longitude)


pal <- colorNumeric(palette= brewer.pal(9,"Reds")[3:9], domain=data$Magnitude)
leaflet(data) %>% addTiles() %>%
  fitBounds(lng1=~min(Longitude),lat1=~min(Latitude),
            lng2=~max(Longitude),lat2=~max(Latitude)) %>%
  addCircles(radius= ~9^Magnitude+2500, weight=1, color=~pal(Magnitude),
             fillColor=~pal(Magnitude),fillOpacity = 0.7,
             popup=~paste("Date:",`Date.UTC`,
                          " / Location: ",Location,
                          " / Magnitude: ",Magnitude)) %>%
  addLegend(position="bottomright",pal=pal,values=~Magnitude)


grid_size <- 0.5
# Create a grid
data <- data %>%
  mutate(
    lon_grid = floor(Longitude / grid_size) * grid_size,
    lat_grid = floor(Latitude / grid_size) * grid_size
  )

grid_data <- data %>%
  group_by(lon_grid, lat_grid) %>%
  summarize(avg_magnitude = mean(Magnitude, na.rm = TRUE))



library(sp)

# Function to create polygons for grid cells
create_grid_polygon <- function(lon, lat, size) {
  Polygon(cbind(
    c(lon, lon + size, lon + size, lon, lon),
    c(lat, lat, lat + size, lat + size, lat)
  ))
}

polygons <- lapply(1:nrow(grid_data), function(i) {
  Polygons(list(create_grid_polygon(grid_data$lon_grid[i], grid_data$lat_grid[i], grid_size)), i)
})

sp_polygons <- SpatialPolygons(polygons)
spdf <- SpatialPolygonsDataFrame(sp_polygons, data = grid_data)

pal <- colorNumeric(palette = brewer.pal(9, "Reds")[3:9], domain = grid_data$avg_magnitude)

leaflet(spdf) %>% addTiles() %>%
  fitBounds(lng1 = ~min(data$Longitude), lat1 = ~min(data$Latitude),
            lng2 = ~max(data$Longitude), lat2 = ~max(data$Latitude)) %>%
  addPolygons(fillColor = ~pal(avg_magnitude), fillOpacity = 0.7, weight = 1, color = "black",
              popup = ~paste("Average Magnitude:", avg_magnitude)) %>%
  addLegend(position = "bottomright", pal = pal, values = ~avg_magnitude, title = "Avg Magnitude")


# Geodata
library(tidyverse) # ggplot2, dplyr, tidyr, readr, purrr, tibble
library(magrittr) # pipes
library(lintr) # code linting
library(sf) # spatial data handling
library(raster) # raster handling (needed for relief)
library(viridis) # viridis color scale
# library(xlsx)
#library(cowplot) # stack ggplots


# read cantonal borders
canton_geo <- read_sf("/Users/jamelbelgacem/Documents/R dev/Earthquake2/sf boudaries/g2k15.shp")

# read country borders
country_geo <- read_sf("/Users/jamelbelgacem/Documents/R dev/Earthquake2/sf boudaries/g2l15.shp")

# read lakes
lake_geo <- read_sf("/Users/jamelbelgacem/Documents/R dev/Earthquake2/sf boudaries/g2s15.shp")

# read productive area (2324 municipalities)
municipality_prod_geo <- read_sf("/Users/jamelbelgacem/Documents/R dev/Earthquake2/sf boudaries/gde-1-1-15.shp")

# Your data are originally geographical coordinates which has EPSG=4326
coords_sf <- st_as_sf(data, coords = c("Longitude", "Latitude"), crs = 4326)
# Then you can transform them to the system you want
coords_earthquakes <- coords_sf %>% st_transform(crs = st_crs(canton_geo))

intersection <- canton_geo %>% 
  st_intersection(coords_earthquakes) %>%
  group_by(KTNAME) %>%
  summarize(count=n()) %>%
  as.data.frame(.)

canton_geo$count <- rep(0,26)
for(i in c(1:26)){
  for(j in c(1:25)){
    if(canton_geo$KTNAME[i]==intersection$KTNAME[j]){
      canton_geo$count[i]=intersection$count[j]
    }
  }
}


ggplot() +
  geom_sf(data = canton_geo, aes(fill = count), color = "black", size = 0.5) +
  geom_sf_text(data = canton_geo, aes(label = paste0(KTNAME, ": ", count)), nudge_x = 0.25, nudge_y = 0.25, size=2.3, check_overlap = TRUE)+
  scale_fill_gradient(low = "green", high = "red", trans="log10", n.breaks=5) +
  theme_void() +
  labs(fill = "Earthquake Count", title = "Earthquakes in Switzerland", subtitle = "Magnitude > 1 between 2015 and 2024")+
  theme(
    plot.title = element_text(size = 18, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 12, face = "bold", hjust = 0.5),
    legend.position = "none"
  )

# read in raster of relief
relief <- raster("/Users/jamelbelgacem/Documents/R dev/Earthquake2/sf boudaries/02-relief-ascii.asc") %>%
  # hide relief outside of Switzerland by masking with country borders
  mask(country_geo) %>%
  as("SpatialPixelsDataFrame") %>%
  as.data.frame() %>%
  rename(value = `X02.relief.ascii`)

# clean up
rm(country_geo)


canton_geo %>%
  left_join(intersection$count)

# Perform spatial join to count points in each polygon
joined <- st_join(coords_earthquakes, canton_geo, join = st_within)

# Count points in each polygon
counts <- joined %>%
  group_by(KTNAME) %>%
  summarise(point_count = n(), .groups = "drop")

polygons_with_counts <- canton_geo %>%
  left_join(counts, by = "KTNAME") %>%
  mutate(point_count = ifelse(is.na(point_count), 0, point_count))

canton_geo2 <- canton_geo %>% 
  st_intersection(coords_cali) %>%
  group_by(KTNAME) %>%
  summarize(count=n()) %>%
  select(c(KTNAME, count)) %>%
  st_join(canton_geo, by=c("KTNAME"="KTNAME"))

df_cantons <- read.csv('/Users/jamelbelgacem/Documents/R dev/Earthquake2/sf boudaries/list_cantons_CH.csv', sep=',')
data_2 <- data %>%
  left_join(df_cantons, by=c("Location"="Name"))

ggplot() +
  geom_sf(data = coords_sf,
          inherit.aes = FALSE,
          color = "#8f6033",
          size = 3,
          alpha = .8)

ggplot() +
  geom_sf(data = canton_geo,
          inherit.aes = FALSE,
          color = "#8f6033",
          size = 3,
          alpha = .8)+
  scale_fill_manual()
canton_geo <- st_join(canton_geo, canton_geo2,)
ggplot() +
  geom_sf(data = canton_geo,
          inherit.aes = FALSE,
          aes(fill = canton_geo2$count),
          color = "#8f6033",
          size = 3,
          alpha = .8) +
  scale_fill_gradient(low = "green", high = "red") +
  theme_minimal()
