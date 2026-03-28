const statusConfig = {
  "visa-free": { label: "免签", color: "#2fd36d" },
  "visa-on-arrival": { label: "落地签", color: "#ffb11a" },
  "e-visa": { label: "电子签", color: "#38c9f2" },
  "visa-required": { label: "需签证", color: "#4f86f7" },
  "no-admission": { label: "禁止入境", color: "#4a5568" },
  unknown: { label: "暂无数据", color: "#1b2435" }
};

const localDataUrl = "./data/passport-index.json";
const localWorldMapUrl = "./data/world.geo.json";
const localGlobeWorldUrl = "./data/world-globe.geojson";
const mapBackgroundColor = "#040b17";
const dimmedColor = "#34435d";

const passportSelect = document.getElementById("passportSelect");
const legendList = document.getElementById("legendList");
const clearFilterButton = document.getElementById("clearFilterButton");
const mapTitle = document.getElementById("mapTitle");
const mapSubtitle = document.getElementById("mapSubtitle");
const hoverInfo = document.getElementById("hoverInfo");
const statPills = Array.from(document.querySelectorAll(".stat-pill"));
const viewButtons = Array.from(document.querySelectorAll(".view-button"));
const worldMapElement = document.getElementById("worldMap");
const globeViewElement = document.getElementById("globeView");

const countElements = {
  "visa-free": document.getElementById("visaFreeCount"),
  "visa-on-arrival": document.getElementById("visaOnArrivalCount"),
  "e-visa": document.getElementById("eVisaCount"),
  "visa-required": document.getElementById("visaRequiredCount")
};

const chineseRegionNames = new Intl.DisplayNames(["zh-CN"], { type: "region" });
const englishRegionNames = new Intl.DisplayNames(["en"], { type: "region" });
const urlParams = new URLSearchParams(window.location.search);

const chineseNameOverrides = {
  XK: "科索沃",
  HK: "中国香港",
  MO: "中国澳门",
  PS: "巴勒斯坦"
};

const englishNameOverrides = {
  XK: "Kosovo",
  HK: "Hong Kong",
  MO: "Macao",
  PS: "Palestine"
};

const mapNameAliases = {
  "Antigua & Barbuda": "Antigua and Barb.",
  "Bosnia & Herzegovina": "Bosnia and Herz.",
  "Bosnia and Herzegovina": "Bosnia and Herz.",
  "Central African Republic": "Central African Rep.",
  "Czechia": "Czech Rep.",
  "Democratic Republic of the Congo": "Dem. Rep. Congo",
  "Dominican Republic": "Dominican Rep.",
  "Equatorial Guinea": "Eq. Guinea",
  "Côte d’Ivoire": "Côte d'Ivoire",
  "North Macedonia": "Macedonia",
  Eswatini: "Swaziland",
  "United States of America": "United States",
  "United States": "United States",
  "South Korea": "Korea",
  "North Korea": "Dem. Rep. Korea",
  "Cape Verde": "Cape Verde",
  Laos: "Lao PDR",
  "Myanmar (Burma)": "Myanmar",
  "South Sudan": "S. Sudan",
  "São Tomé & Príncipe": "São Tomé and Principe",
  "Trinidad & Tobago": "Trinidad and Tobago",
  Türkiye: "Turkey",
  "St. Vincent & Grenadines": "St. Vin. and Gren.",
  "St. Kitts & Nevis": "Saint Kitts and Nevis",
  "St. Lucia": "Saint Lucia",
  Macao: "Macao",
  Taiwan: "Taiwan",
  Kosovo: "Kosovo"
};

const chart = echarts.init(worldMapElement);
let globe = null;
let passportList = [];
let currentPassport = null;
let activeStatusFilter = null;
let currentView = "2d";
let worldMapJsonCache = null;
let globeWorldJsonCache = null;
let featureNameSet = new Set();
let currentGlobeFeatures = [];
let hoveredCountryCode = null;

createLegend();
bindEvents();
loadInitialResources();

window.addEventListener("resize", () => {
  chart.resize();
  resizeGlobe();
});

chart.on("mousemove", (params) => {
  if (currentView !== "2d") {
    return;
  }

  if (params?.data) {
    updateHoverInfo(params.data);
  } else {
    resetHoverInfo();
  }
});

chart.on("globalout", () => {
  if (currentView === "2d") {
    resetHoverInfo();
  }
});

function bindEvents() {
  passportSelect.addEventListener("change", (event) => {
    activeStatusFilter = null;
    renderPassport(event.target.value);
  });

  clearFilterButton.addEventListener("click", () => {
    activeStatusFilter = null;
    refreshMap();
  });

  statPills.forEach((pill) => {
    pill.addEventListener("click", () => {
      toggleStatusFilter(pill.dataset.statusFilter);
    });
  });

  viewButtons.forEach((button) => {
    button.addEventListener("click", () => {
      currentView = button.dataset.view;
      hoveredCountryCode = null;
      resetHoverInfo();
      updateViewButtons();
      refreshMap();
    });
  });
}

function createLegend() {
  const legendOrder = ["visa-free", "e-visa", "visa-on-arrival", "visa-required"];

  legendList.innerHTML = legendOrder
    .map((statusKey) => {
      const item = statusConfig[statusKey];
      return `
        <li>
          <button class="legend-button" type="button" data-status-filter="${statusKey}">
            <span class="legend-color" style="background:${item.color}"></span>
            <span>${item.label}</span>
          </button>
        </li>
      `;
    })
    .join("");

  legendList.querySelectorAll(".legend-button").forEach((button) => {
    button.addEventListener("click", () => {
      toggleStatusFilter(button.dataset.statusFilter);
    });
  });
}

async function loadInitialResources() {
  passportSelect.disabled = true;
  mapSubtitle.textContent = "正在读取本地数据和地图";

  try {
    const [dataResponse, worldMapResponse, globeWorldResponse] = await Promise.all([
      fetch(localDataUrl),
      fetch(localWorldMapUrl),
      fetch(localGlobeWorldUrl)
    ]);

    if (!dataResponse.ok) {
      throw new Error(`本地数据读取失败，状态码 ${dataResponse.status}`);
    }

    if (!worldMapResponse.ok) {
      throw new Error(`本地地图读取失败，状态码 ${worldMapResponse.status}`);
    }

    if (!globeWorldResponse?.ok) {
      throw new Error(`本地地球地图读取失败，状态码 ${globeWorldResponse?.status}`);
    }

    const [rawData, worldMapJson, globeWorldJson] = await Promise.all([
      dataResponse.json(),
      worldMapResponse.json(),
      globeWorldResponse.json()
    ]);

    worldMapJsonCache = worldMapJson;
    globeWorldJsonCache = globeWorldJson;
    featureNameSet = new Set(worldMapJson.features.map((feature) => feature.properties?.name).filter(Boolean));
    echarts.registerMap("world", worldMapJson);

    passportList = buildPassportListFromJson(rawData);

    if (!passportList.length) {
      throw new Error("没有可用护照数据");
    }

    createPassportOptions();
    passportSelect.disabled = false;
    renderPassport(getInitialPassportCode());
  } catch (error) {
    console.error(error);
    mapSubtitle.textContent = "本地资源读取失败，请用 start.bat 打开页面";
  }
}

function createPassportOptions() {
  passportSelect.innerHTML = passportList
    .map((passport) => `<option value="${passport.code}">${passport.nameZh}</option>`)
    .join("");
}

function getInitialPassportCode() {
  const preferredCode = (urlParams.get("passports") || "").toUpperCase();
  const matchedPassport = passportList.find((passport) => passport.code === preferredCode);
  return matchedPassport ? matchedPassport.code : passportList[0].code;
}

function renderPassport(passportCode) {
  currentPassport = passportList.find((passport) => passport.code === passportCode);

  if (!currentPassport) {
    return;
  }

  passportSelect.value = currentPassport.code;
  updateStats(currentPassport.destinations);
  hoveredCountryCode = null;
  resetHoverInfo();
  refreshMap();
}

function refreshMap() {
  if (!currentPassport || !worldMapJsonCache) {
    return;
  }

  mapTitle.textContent = `${currentPassport.nameZh}护照签证地图`;
  mapSubtitle.textContent = buildSubtitle();
  updateFilterUI();
  updateViewButtons();
  updateSurfaceVisibility();

  if (currentView === "3d") {
    drawGlobe(currentPassport, activeStatusFilter);
  } else {
    drawMap(currentPassport, activeStatusFilter);
  }
}

function buildSubtitle() {
  if (activeStatusFilter) {
    return currentView === "3d"
      ? `现在是可拖动旋转的 3D 地球，只看${statusConfig[activeStatusFilter].label}`
      : `当前只看${statusConfig[activeStatusFilter].label}`;
  }

  return currentView === "3d"
    ? "现在是可拖动旋转的 3D 地球，鼠标放到国家上会显示名称和签证状态"
    : "数据已经放在本地，点底部图例或数字，只高亮某一类";
}

function toggleStatusFilter(statusKey) {
  activeStatusFilter = activeStatusFilter === statusKey ? null : statusKey;
  refreshMap();
}

function updateFilterUI() {
  legendList.querySelectorAll(".legend-button").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.statusFilter === activeStatusFilter);
  });

  statPills.forEach((pill) => {
    pill.classList.toggle("is-active", pill.dataset.statusFilter === activeStatusFilter);
  });
}

function updateViewButtons() {
  viewButtons.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.view === currentView);
  });
}

function updateSurfaceVisibility() {
  worldMapElement.classList.toggle("is-visible", currentView === "2d");
  globeViewElement.classList.toggle("is-visible", currentView === "3d");
  document.body.classList.toggle("is-3d-view", currentView === "3d");
}

function updateStats(destinations) {
  const counts = {
    "visa-free": 0,
    "visa-on-arrival": 0,
    "e-visa": 0,
    "visa-required": 0
  };

  destinations.forEach((destination) => {
    if (counts[destination.status] !== undefined) {
      counts[destination.status] += 1;
    }
  });

  Object.entries(counts).forEach(([statusKey, count]) => {
    countElements[statusKey].textContent = String(count);
  });
}

function drawMap(passport, statusFilter) {
  chart.clear();
  chart.setOption({
    backgroundColor: mapBackgroundColor,
    tooltip: {
      trigger: "item",
      backgroundColor: "rgba(11, 18, 31, 0.95)",
      borderColor: "rgba(127, 156, 201, 0.18)",
      textStyle: { color: "#eef4ff" },
      formatter(params) {
        return renderTooltip(params.data, params.name);
      }
    },
    series: [
      {
        type: "map",
        map: "world",
        roam: true,
        zoom: 1.16,
        left: "center",
        top: "5%",
        itemStyle: {
          areaColor: statusConfig.unknown.color,
          borderColor: "#2f3f5e",
          borderWidth: 0.7
        },
        emphasis: {
          label: { show: false },
          itemStyle: {
            areaColor: "#f8fbff",
            borderColor: "#c8dcff",
            borderWidth: 1.1
          }
        },
        data: buildMapData(passport, statusFilter)
      }
    ]
  });
}

function drawGlobe(passport, statusFilter) {
  ensureGlobe();
  currentGlobeFeatures = buildGlobeFeatures(passport, statusFilter);

  globe
    .polygonsData(currentGlobeFeatures)
    .polygonLabel((feature) => renderTooltip(feature.__meta, feature.properties?.ADMIN || feature.properties?.NAME || "未知地区"))
    .onPolygonHover((feature) => {
      hoveredCountryCode = feature?.__meta?.countryCode || null;
      updateHoverInfo(feature?.__meta || null);
      applyGlobeStyle();
    });

  applyGlobeStyle();
  resizeGlobe();
}

function ensureGlobe() {
  if (globe || typeof Globe !== "function") {
    return;
  }

  globe = new Globe(globeViewElement)
    .backgroundColor(mapBackgroundColor)
    .showAtmosphere(true)
    .atmosphereColor("#73b9ff")
    .atmosphereAltitude(0.14)
    .lineHoverPrecision(0)
    .polygonsTransitionDuration(160);

  if (typeof globe.globeImageUrl === "function") {
    globe.globeImageUrl(false);
  }

  if (typeof globe.bumpImageUrl === "function") {
    globe.bumpImageUrl(false);
  }

  if (typeof globe.pointOfView === "function") {
    globe.pointOfView({ lat: 20, lng: 25, altitude: 2.6 }, 0);
  }

  const material = typeof globe.globeMaterial === "function" ? globe.globeMaterial() : null;
  if (material) {
    material.color?.set?.("#10203a");
    material.emissive?.set?.("#0b1730");
    material.emissiveIntensity = 0.45;
    material.shininess = 0.8;
  }

  const controls = typeof globe.controls === "function" ? globe.controls() : null;
  if (controls) {
    controls.enablePan = false;
    controls.minDistance = 160;
    controls.maxDistance = 340;
    controls.rotateSpeed = 0.85;
    controls.zoomSpeed = 0.9;
  }
}

function applyGlobeStyle() {
  if (!globe) {
    return;
  }

  globe
    .polygonCapColor((feature) => getGlobeCapColor(feature))
    .polygonSideColor((feature) => getGlobeSideColor(feature))
    .polygonStrokeColor((feature) => getGlobeStrokeColor(feature))
    .polygonAltitude((feature) => getGlobeAltitude(feature));
}

function resizeGlobe() {
  if (!globe || currentView !== "3d") {
    return;
  }

  const width = globeViewElement.clientWidth || window.innerWidth;
  const height = globeViewElement.clientHeight || window.innerHeight;
  globe.width(width).height(height);
}

function buildMapData(passport, statusFilter) {
  return passport.destinations
    .map((destination) => {
      const featureName = resolveFeatureName(destination.nameEn);
      if (!featureName) {
        return null;
      }

      const statusInfo = statusConfig[destination.status] || statusConfig.unknown;
      const isActive = !statusFilter || destination.status === statusFilter;

      return {
        name: featureName,
        value: isActive ? 1 : 0,
        itemStyle: {
          areaColor: isActive ? statusInfo.color : dimmedColor,
          opacity: isActive ? 1 : 0.58
        },
        countryCode: destination.code,
        countryNameZh: destination.nameZh,
        countryNameEn: destination.nameEn,
        statusLabel: statusInfo.label,
        stayDays: destination.stayDays || null,
        isDimmed: !isActive
      };
    })
    .filter(Boolean);
}

function buildGlobeFeatures(passport, statusFilter) {
  return globeWorldJsonCache.features
    .filter((feature) => {
      const featureName = feature?.properties?.ADMIN || feature?.properties?.NAME;
      return featureName && featureName !== "Antarctica";
    })
    .map((feature) => {
      const featureCode = getGlobeFeatureCode(feature);
      const destination = (featureCode && passport.destinations.find((item) => item.code === featureCode)) || null;
      const statusInfo = destination ? statusConfig[destination.status] || statusConfig.unknown : statusConfig.unknown;
      const isActive = destination ? !statusFilter || destination.status === statusFilter : false;

      return {
        ...feature,
        __meta: {
          countryCode: destination?.code || null,
          countryNameZh: destination?.nameZh || feature.properties.ADMIN || feature.properties.NAME,
          countryNameEn: destination?.nameEn || feature.properties.ADMIN || feature.properties.NAME,
          statusLabel: destination ? statusInfo.label : statusConfig.unknown.label,
          stayDays: destination?.stayDays || null,
          isDimmed: destination ? !isActive : true,
          statusKey: destination?.status || "unknown"
        }
      };
    });
}

function resolveFeatureName(englishName) {
  const aliasName = mapNameAliases[englishName] || englishName;
  if (featureNameSet.has(aliasName)) {
    return aliasName;
  }
  return featureNameSet.has(englishName) ? englishName : null;
}

function getGlobeFeatureCode(feature) {
  const properties = feature?.properties || {};
  const directCode = properties.ISO_A2;

  if (directCode && directCode !== "-99") {
    return directCode;
  }

  const adminName = properties.ADMIN || properties.NAME || "";
  const codeByAdmin = {
    France: "FR",
    Norway: "NO",
    "Northern Cyprus": "CY",
    Somaliland: "SO"
  };

  return codeByAdmin[adminName] || null;
}

function getGlobeCapColor(feature) {
  const meta = feature.__meta;
  const statusInfo = statusConfig[meta.statusKey] || statusConfig.unknown;

  if (!meta.countryCode) {
    return "rgba(27, 36, 53, 0.92)";
  }
  if (meta.countryCode === hoveredCountryCode) {
    return "#f8fbff";
  }
  if (meta.isDimmed) {
    return "rgba(52, 67, 93, 0.76)";
  }
  return statusInfo.color;
}

function getGlobeSideColor(feature) {
  const meta = feature.__meta;
  if (!meta.countryCode) {
    return "rgba(27, 36, 53, 0.78)";
  }
  if (meta.countryCode === hoveredCountryCode) {
    return "rgba(255, 255, 255, 0.2)";
  }
  return meta.isDimmed ? "rgba(52, 67, 93, 0.3)" : "rgba(186, 214, 255, 0.12)";
}

function getGlobeStrokeColor(feature) {
  const meta = feature.__meta;
  if (meta.countryCode === hoveredCountryCode) {
    return "#ffffff";
  }
  return meta.isDimmed ? "rgba(65, 81, 108, 0.92)" : "#2f3f5e";
}

function getGlobeAltitude(feature) {
  const meta = feature.__meta;
  const baseAltitude = meta.countryCode ? (meta.isDimmed ? 0.004 : 0.018) : 0.003;
  return meta.countryCode === hoveredCountryCode ? baseAltitude + 0.04 : baseAltitude;
}

function renderTooltip(data, fallbackName) {
  if (!data) {
    return `<strong>${fallbackName}</strong><br/>暂无数据`;
  }

  const stayText = data.stayDays ? `<br/>停留时长：${data.stayDays} 天` : "";
  const filterText = data.isDimmed ? "<br/>当前筛选下未高亮" : "";

  return `
    <strong>${data.countryNameZh || fallbackName}</strong><br/>
    状态：${data.statusLabel}
    ${stayText}
    ${filterText}
  `;
}

function updateHoverInfo(data) {
  if (!data) {
    resetHoverInfo();
    return;
  }
  hoverInfo.textContent = `当前悬停：${data.countryNameZh} | ${data.statusLabel}`;
}

function resetHoverInfo() {
  hoverInfo.textContent = "当前悬停：暂无";
}

function buildPassportListFromJson(rawData) {
  return Object.keys(rawData)
    .sort((codeA, codeB) => getChineseCountryName(codeA).localeCompare(getChineseCountryName(codeB), "zh-CN"))
    .map((passportCode) => {
      const destinations = Object.entries(rawData[passportCode]).map(([destinationCode, visaInfo]) => ({
        code: destinationCode,
        nameZh: getChineseCountryName(destinationCode),
        nameEn: getEnglishCountryName(destinationCode),
        status: normalizeStatus(visaInfo.status),
        stayDays: visaInfo.days || null
      }));

      return {
        code: passportCode,
        nameZh: getChineseCountryName(passportCode),
        nameEn: getEnglishCountryName(passportCode),
        destinations
      };
    });
}

function normalizeStatus(rawStatus) {
  if (!rawStatus) {
    return "unknown";
  }

  const normalized = rawStatus.toLowerCase();
  const statusMap = {
    "visa free": "visa-free",
    "visa on arrival": "visa-on-arrival",
    eta: "e-visa",
    "e-visa": "e-visa",
    "visa required": "visa-required",
    "no admission": "no-admission"
  };

  return statusMap[normalized] || "unknown";
}

function getChineseCountryName(code) {
  return chineseNameOverrides[code] || chineseRegionNames.of(code) || code;
}

function getEnglishCountryName(code) {
  return englishNameOverrides[code] || englishRegionNames.of(code) || code;
}
