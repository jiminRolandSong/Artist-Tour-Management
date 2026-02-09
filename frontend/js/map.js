/* =============================================================================
   Map Utilities (Leaflet)
============================================================================= */

const MapManager = {
  instances: new Map(),

  create(elementId, options = {}) {
    const el = document.getElementById(elementId);
    if (!el || typeof L === "undefined") return null;

    // Return existing instance
    if (this.instances.has(elementId)) {
      return this.instances.get(elementId);
    }

    const map = L.map(elementId).setView(options.center || [20, 0], options.zoom || 2);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: "&copy; OpenStreetMap contributors"
    }).addTo(map);

    const instance = {
      map,
      markers: [],
      polylines: [],

      clearMarkers() {
        this.markers.forEach(m => map.removeLayer(m));
        this.markers = [];
      },

      clearPolylines() {
        this.polylines.forEach(p => map.removeLayer(p));
        this.polylines = [];
      },

      clear() {
        this.clearMarkers();
        this.clearPolylines();
      },

      addMarker(lat, lon, label, options = {}) {
        if (!lat || !lon) return null;

        let marker;
        if (options.circle) {
          marker = L.circleMarker([Number(lat), Number(lon)], {
            radius: options.radius || 6,
            color: options.color || "#c26b2b",
            weight: 2,
            fillOpacity: 0.9
          });
        } else {
          marker = L.marker([Number(lat), Number(lon)]);
        }

        if (label) {
          marker.bindPopup(label);
        }

        marker.addTo(map);
        this.markers.push(marker);
        return marker;
      },

      addPolyline(points, options = {}) {
        const polyline = L.polyline(points, {
          color: options.color || "#1f7a63",
          weight: options.weight || 3,
          opacity: options.opacity || 0.85
        });

        polyline.addTo(map);
        this.polylines.push(polyline);
        return polyline;
      },

      fitBounds(padding = [30, 30]) {
        const allPoints = this.markers.map(m => m.getLatLng());
        if (allPoints.length > 1) {
          map.fitBounds(allPoints.map(p => [p.lat, p.lng]), { padding });
        } else if (allPoints.length === 1) {
          map.setView([allPoints[0].lat, allPoints[0].lng], 6);
        }
      },

      renderTours(tours) {
        this.clearMarkers();

        const coords = tours
          .map(t => ({
            lat: t.venue?.latitude,
            lon: t.venue?.longitude,
            label: `${t.artist?.name} @ ${t.venue?.name} (${t.date})`
          }))
          .filter(c => c.lat && c.lon);

        coords.forEach(c => this.addMarker(c.lat, c.lon, c.label));
        this.fitBounds();
      },

      renderRoutes(baselineRoute, optimizedRoute, venuesById) {
        this.clear();

        const routeToLatLng = (route) =>
          route
            .map(id => venuesById.get(Number(id)))
            .filter(v => v && v.latitude && v.longitude)
            .map(v => ({
              lat: Number(v.latitude),
              lon: Number(v.longitude),
              name: v.name
            }));

        const baselinePoints = baselineRoute ? routeToLatLng(baselineRoute) : [];
        const optimizedPoints = optimizedRoute ? routeToLatLng(optimizedRoute) : [];

        const addRoute = (points, color) => {
          if (!points.length) return;

          const latlngs = points.map(p => [p.lat, p.lon]);
          this.addPolyline(latlngs, { color });

          points.forEach((p, idx) => {
            this.addMarker(p.lat, p.lon, `${idx + 1}. ${p.name}`, {
              circle: true,
              color
            });
          });
        };

        addRoute(baselinePoints, "#c0392b");
        addRoute(optimizedPoints, "#1f7a63");

        this.fitBounds([20, 20]);
      }
    };

    this.instances.set(elementId, instance);
    return instance;
  },

  get(elementId) {
    return this.instances.get(elementId);
  },

  destroy(elementId) {
    const instance = this.instances.get(elementId);
    if (instance) {
      instance.map.remove();
      this.instances.delete(elementId);
    }
  }
};

window.MapManager = MapManager;
