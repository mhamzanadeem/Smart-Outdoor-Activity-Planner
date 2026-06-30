import {
  Thermometer,
  Droplets,
  Wind,
  Eye,
  CloudRain,
  Sun,
  Moon,
  MapPin,
} from "lucide-react";

function Stat({ icon: Icon, label, value, accent = "text-gray-300" }) {
  return (
    <div className="weather-stat">
      <Icon className={`w-4 h-4 ${accent}`} />
      <span className={`text-sm font-semibold ${accent}`}>{value}</span>
      <span className="text-[10px] text-gray-500 uppercase tracking-wider text-center leading-tight">
        {label}
      </span>
    </div>
  );
}

function conditionBadgeColor(condition) {
  const c = condition?.toLowerCase() || "";
  if (c.includes("clear") || c.includes("sun")) return "bg-amber-900/50 text-amber-300 border-amber-800";
  if (c.includes("cloud")) return "bg-gray-700/70 text-gray-300 border-gray-600";
  if (c.includes("rain") || c.includes("drizzle")) return "bg-blue-900/50 text-blue-300 border-blue-800";
  if (c.includes("thunder") || c.includes("storm")) return "bg-purple-900/50 text-purple-300 border-purple-800";
  if (c.includes("snow")) return "bg-sky-900/50 text-sky-200 border-sky-700";
  if (c.includes("mist") || c.includes("fog") || c.includes("haze")) return "bg-teal-900/50 text-teal-300 border-teal-800";
  return "bg-gray-700/50 text-gray-300 border-gray-600";
}

function rainColor(prob) {
  if (prob >= 60) return "text-blue-400";
  if (prob >= 30) return "text-sky-400";
  return "text-emerald-400";
}

export default function WeatherCard({ data }) {
  if (!data) return null;
  const {
    city,
    temperature_c,
    feels_like_c,
    humidity_percent,
    wind_speed_kmh,
    visibility_km,
    condition,
    description,
    rain_probability_percent,
    is_daytime,
  } = data;

  return (
    <div className="weather-card animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-1.5 text-gray-400 text-xs mb-1">
            <MapPin className="w-3 h-3" />
            <span className="font-medium">{city}</span>
          </div>
          <div
            className={`tool-badge border ${conditionBadgeColor(condition)}`}
          >
            {is_daytime ? (
              <Sun className="w-3 h-3" />
            ) : (
              <Moon className="w-3 h-3" />
            )}
            {description}
          </div>
        </div>
        <div className="text-right">
          <div className="text-3xl font-bold text-white leading-none">
            {Math.round(temperature_c)}°C
          </div>
          <div className="text-xs text-gray-500 mt-1">
            Feels like {Math.round(feels_like_c)}°C
          </div>
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-4 gap-2">
        <Stat
          icon={Droplets}
          label="Humidity"
          value={`${humidity_percent}%`}
          accent={humidity_percent > 70 ? "text-blue-400" : "text-sky-300"}
        />
        <Stat
          icon={Wind}
          label="Wind"
          value={`${wind_speed_kmh} km/h`}
          accent={wind_speed_kmh > 30 ? "text-orange-400" : "text-teal-300"}
        />
        <Stat
          icon={Eye}
          label="Visibility"
          value={`${visibility_km} km`}
          accent={visibility_km < 4 ? "text-red-400" : "text-violet-300"}
        />
        <Stat
          icon={CloudRain}
          label="Rain Prob."
          value={`${rain_probability_percent}%`}
          accent={rainColor(rain_probability_percent)}
        />
      </div>
    </div>
  );
}
