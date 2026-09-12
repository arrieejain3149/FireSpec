import { useState } from 'react';
import axios from 'axios';
import DeckGL from '@deck.gl/react';
import { HexagonLayer } from '@deck.gl/aggregation-layers';
import Map from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';
import { BarChart, Bar, XAxis, YAxis, Tooltip as RechartsTooltip, ResponsiveContainer, Scatter, ComposedChart, Line, CartesianGrid, Label } from 'recharts';

const SATELLITE_STYLE = {
  version: 8,
  sources: {
    'esri-satellite': {
      type: 'raster',
      tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'],
      tileSize: 256
    }
  },
  layers: [
    {
      id: 'satellite',
      type: 'raster',
      source: 'esri-satellite',
      minzoom: 0,
      maxzoom: 19
    }
  ]
};

function App() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [hoverInfo, setHoverInfo] = useState<any>(null);
  const [activeFeature, setActiveFeature] = useState<string | null>(null);

  const handleFileUpload = async (event: any) => {
    const file = event.target.files[0];
    event.target.value = null; // Reset input so the same file can be uploaded again
    if (!file) return;

    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await axios.post(`${apiUrl}/predict`, formData);
      setData(response.data);
    } catch (error) {
      console.error('Error uploading file', error);
    }
    setLoading(false);
  };

  const handleDownloadCSV = () => {
    if (!data) return;
    const csvContent = "data:text/csv;charset=utf-8," 
      + Object.keys(data.raw_table[0]).join(",") + "\n"
      + data.raw_table.map((row: any) => Object.values(row).join(",")).join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "optimized_dispatch.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleNasaFirmsSync = async () => {
    setLoading(true);
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await axios.get(`${apiUrl}/nasa-firms`);
      setData(response.data);
    } catch (error) {
      console.error('Error fetching NASA FIRMS data', error);
    }
    setLoading(false);
  };

  const layers: any[] = [];
  if (data) {
    layers.push(
      new HexagonLayer({
        id: 'hex',
        data: data.portfolio,
        getPosition: (d: any) => [d.lon, d.lat],
        radius: 400,
        extruded: false, 
        getColorWeight: (d: any) => {
          if (!activeFeature) return Number(d.ranking_score || 0);
          return Number(d[activeFeature] || 0);
        },
        colorAggregation: 'MEAN',
        updateTriggers: {
          getColorWeight: [activeFeature]
        },
        colorRange: activeFeature ? [
          [241, 245, 249, 150],  // Light Slate
          [148, 163, 184, 255],  // Slate
          [71, 85, 105, 255],    // Dark Slate
          [15, 23, 42, 255]      // Near Black (High parameter value)
        ] : [
          [241, 245, 249, 150],  // Light gray (1)
          [148, 163, 184, 255],  // Solid slate (2)
          [249, 115, 22, 255],   // Orange (3)
          [220, 38, 38, 255]     // Red (4 - Capacity)
        ],
        pickable: true,
        onHover: (info) => setHoverInfo(info.object ? info : null)
      })
    );
  }

  return (
    <div className="w-screen min-h-screen bg-[#F8F9FA] text-[#111111] p-6 lg:p-12 selection:bg-black selection:text-white flex flex-col">
      
      {/* Dynamic Hover Tooltip */}
      {hoverInfo && hoverInfo.object && hoverInfo.object.points && hoverInfo.object.points.length > 0 && (
        <div 
          className="absolute z-50 bg-white border-2 border-black p-4 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] text-xs pointer-events-none w-72"
          style={{left: hoverInfo.x + 15, top: hoverInfo.y + 15}}
        >
          <div className="font-bold text-black border-b-2 border-black pb-2 mb-2 uppercase tracking-wide flex justify-between">
            <span>GPS: {Number(hoverInfo.object.points[0]?.lat || 0).toFixed(4)}, {Number(hoverInfo.object.points[0]?.lon || 0).toFixed(4)}</span>
            <span className="text-[#666]">[{hoverInfo.object.points[0]?.X}, {hoverInfo.object.points[0]?.Y}]</span>
          </div>
          
          <div className="mb-2 border-b-2 border-black pb-2">
             <div className="flex justify-between mb-1">
               <span className="text-[#666] font-bold">TYPE:</span>
               <span className="font-bold text-black text-right">{hoverInfo.object.points[0]?.fire_type || 'Unknown'}</span>
             </div>
             <div className="flex justify-between mb-1">
               <span className="text-[#666] font-bold">INDUSTRY:</span>
               <span className="font-bold text-black text-right">{hoverInfo.object.points[0]?.industry_sector || 'Unknown'}</span>
             </div>
             <div className="flex justify-between">
               <span className="text-[#DC2626] font-bold">HAZARD SCORE:</span>
               <span className="font-bold text-[#DC2626]">{Number(hoverInfo.object.points[0]?.ranking_score || 0).toFixed(4)}</span>
             </div>
          </div>

          <div className="grid grid-cols-2 gap-2 font-mono text-[10px] mt-2">
             <div><span className="text-[#888]">TEMP:</span> {hoverInfo.object.points[0]?.temp || 0}°C</div>
             <div><span className="text-[#888]">WIND:</span> {hoverInfo.object.points[0]?.wind || 0}km/h</div>
             <div><span className="text-[#888]">RH:</span> {hoverInfo.object.points[0]?.RH || 0}%</div>
             <div><span className="text-[#888]">FFMC:</span> {hoverInfo.object.points[0]?.FFMC || 0}</div>
          </div>
        </div>
      )}

      {/* Header */}
      <header className="flex justify-between items-center mb-10 pb-6 border-b-2 border-black shrink-0">
        <div>
          <img src="/firespec-logo.png" alt="FireSpec" className="h-10 object-contain mix-blend-multiply" />
        </div>
        <div className="flex gap-4">
          <button 
            onClick={handleNasaFirmsSync}
            className="cursor-pointer border-2 border-[#DC2626] text-[#DC2626] bg-white px-6 py-2 font-bold text-sm tracking-wider uppercase hover:bg-[#DC2626] hover:text-white transition-colors shadow-[4px_4px_0px_0px_rgba(220,38,38,1)]"
          >
            Sync Live NASA FIRMS
          </button>
          <label className="cursor-pointer border-2 border-black bg-white px-6 py-2 font-bold text-sm tracking-wider uppercase hover:bg-black hover:text-white transition-colors shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
            Upload CSV File
            <input type="file" className="hidden" onChange={handleFileUpload} />
          </label>
        </div>
      </header>

      {/* Loading State */}
      {loading && (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center text-black font-bold uppercase tracking-widest text-2xl">
            Processing Satellite Data...
          </div>
        </div>
      )}

      {/* Empty State / Landing Intro */}
      {!data && !loading && (
        <div className="flex-1 flex flex-col items-center justify-center text-center px-4">
          <h1 className="text-5xl md:text-7xl font-black uppercase tracking-tighter mb-6 text-black">
            Analyze Fire Risk
          </h1>
          <p className="text-lg md:text-xl text-[#555] font-medium mb-12 max-w-2xl">
            Upload your environmental CSV or directly sync live satellite telemetry from the NASA FIRMS network.
          </p>
          <div className="flex gap-6">
            <button 
              onClick={handleNasaFirmsSync}
              className="cursor-pointer border-4 border-[#DC2626] text-[#DC2626] bg-white px-10 py-5 font-black text-xl tracking-widest uppercase hover:bg-[#DC2626] hover:text-white transition-colors shadow-[8px_8px_0px_0px_rgba(220,38,38,1)]"
            >
              Sync Live NASA Data
            </button>
            <label className="cursor-pointer border-4 border-black bg-white px-10 py-5 font-black text-xl tracking-widest uppercase hover:bg-black hover:text-white transition-colors shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]">
              Upload CSV File
              <input type="file" className="hidden" onChange={handleFileUpload} />
            </label>
          </div>

          <div className="mt-20 grid grid-cols-1 md:grid-cols-3 gap-8 text-left max-w-4xl w-full border-t-2 border-black pt-12">
            <div>
              <h3 className="font-bold text-lg uppercase tracking-wide border-b-2 border-black pb-2 mb-3">1. Satellite Sync</h3>
              <p className="text-sm font-medium text-[#555]">Pull direct VIIRS C2 data from the NASA Fire Information System.</p>
            </div>
            <div>
              <h3 className="font-bold text-lg uppercase tracking-wide border-b-2 border-black pb-2 mb-3">2. Upload</h3>
              <p className="text-sm font-medium text-[#555]">Select the data file from your computer to start the engine.</p>
            </div>
            <div>
              <h3 className="font-bold text-lg uppercase tracking-wide border-b-2 border-black pb-2 mb-3">3. Review</h3>
              <p className="text-sm font-medium text-[#555]">View the generated risk map, charts, and raw tables.</p>
            </div>
          </div>
        </div>
      )}

      {/* Data Dashboard */}
      {data && (
        <div className="flex flex-col gap-10 pb-12">
          
          {/* Top Row: Analytics & Map */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
            
            {/* Left: Feature Importance */}
            <div className="bg-white border-2 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] p-8 flex flex-col h-[500px]">
              <h3 className="text-xl font-bold mb-2 uppercase tracking-wide border-b-2 border-black pb-4">
                Feature Importance
              </h3>
              <p className="text-[#666] text-sm mb-6 mt-4">
                Hover over a feature to isolate its geographic impact on the H3 map.
              </p>
              <div className="flex-1 min-h-0">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart 
                    data={data.feature_importance} 
                    layout="vertical" 
                    margin={{ left: 20, bottom: 20 }}
                    onMouseLeave={() => setActiveFeature(null)}
                  >
                    <XAxis type="number" stroke="#000" tick={{fill: '#000', fontSize: 12}}>
                      <Label value="Relative Score" position="insideBottom" offset={-15} fill="#000" fontSize={12} fontWeight="bold" />
                    </XAxis>
                    <YAxis dataKey="name" type="category" width={80} stroke="#000" tick={{fill: '#000', fontSize: 12, fontWeight: 'bold'}} />
                    <RechartsTooltip cursor={{fill: '#F1F5F9'}} contentStyle={{backgroundColor: '#FFF', border: '2px solid #000', borderRadius: '0', fontWeight: 'bold'}}/>
                    <Bar 
                      dataKey="value" 
                      fill="#000" 
                      style={{ cursor: 'pointer' }}
                      onMouseEnter={(data) => setActiveFeature(data.name)}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Right: H3 Map */}
            <div className="bg-white border-2 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] relative h-[500px] flex flex-col">
               <div className="absolute top-0 left-0 z-10 bg-white border-r-2 border-b-2 border-black px-6 py-4 pointer-events-none">
                  <h4 className="font-bold text-black mb-2 uppercase tracking-wide">
                    H3 Tracker {activeFeature && <span className="text-[#DC2626]">[{activeFeature}]</span>}
                  </h4>
                  {!activeFeature ? (
                    <>
                      <p className="text-sm font-bold text-[#64748B]">Slate: Surface Fire</p>
                      <p className="text-sm font-bold text-[#F97316]">Orange: Ground Fire</p>
                      <p className="text-sm font-bold text-[#DC2626]">Red: Crown Fire</p>
                    </>
                  ) : (
                    <p className="text-sm font-bold text-[#555] max-w-xs mt-1">
                      Map rendering isolated intensity of <span className="text-black font-black uppercase">{activeFeature}</span>.
                    </p>
                  )}
               </div>
               <div className="flex-1 relative">
                 <DeckGL
                   initialViewState={{ longitude: -8.85, latitude: 38.5, zoom: 10, pitch: 0, bearing: 0 }}
                   controller={true}
                   layers={layers}
                 >
                   <Map mapStyle={SATELLITE_STYLE as any} />
                 </DeckGL>
               </div>
            </div>

          </div>

          {/* Bottom Row: Regression Plot & Data Table */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
            
            {/* Regression Plot */}
            <div className="bg-white border-2 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] p-8 h-[550px] flex flex-col relative">
              <div className="flex justify-between items-start mb-4 border-b-2 border-black pb-4">
                <div>
                  <h3 className="text-xl font-bold uppercase tracking-wide">Prediction Precision</h3>
                  <p className="text-[#666] text-sm mt-1 max-w-sm">
                    Variance scatter plotting actual inputs vs predicted severity. 
                    Tighter clustering around the red trendline indicates higher model confidence.
                  </p>
                </div>
                <div className="bg-[#F8F9FA] border-2 border-black px-4 py-2 font-bold font-mono text-sm shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] whitespace-nowrap">
                  {data.regression.equation}
                </div>
              </div>

              <div className="flex-1 min-h-0 mt-4 relative">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart margin={{ top: 10, right: 20, bottom: 20, left: 30 }}>
                    <CartesianGrid strokeDasharray="4 4" stroke="#D4D4D8" vertical={false} />
                    <XAxis 
                      type="number" 
                      dataKey="x" 
                      stroke="#000" 
                      domain={['dataMin', 'dataMax']} 
                      tick={{fontSize: 11, fontWeight: 'bold'}}
                      tickFormatter={(val) => val.toFixed(2)}
                    >
                      <Label value={data.regression.xLabel} position="bottom" offset={0} fill="#000" fontSize={12} fontWeight="bold" />
                    </XAxis>
                    <YAxis 
                      type="number" 
                      dataKey="y" 
                      stroke="#000" 
                      domain={['dataMin', 'dataMax']} 
                      tick={{fontSize: 11, fontWeight: 'bold'}}
                      tickFormatter={(val) => val.toFixed(2)}
                      width={50}
                    >
                      <Label value={data.regression.yLabel} angle={-90} position="insideLeft" style={{ textAnchor: 'middle' }} fill="#000" fontSize={12} fontWeight="bold" />
                    </YAxis>
                    <RechartsTooltip 
                      cursor={{strokeDasharray: '3 3', stroke: '#000'}} 
                      contentStyle={{backgroundColor: '#FFF', border: '2px solid #000', borderRadius: '0', fontWeight: 'bold', boxShadow: '4px 4px 0px 0px rgba(0,0,0,1)'}}
                      formatter={(val: any) => typeof val === 'number' ? val.toFixed(4) : val}
                    />
                    <Scatter data={data.regression.data} fill="#000" fillOpacity={0.4} line={false} />
                    <Line data={data.regression.trendline} dataKey="line" stroke="#DC2626" strokeWidth={4} dot={false} activeDot={false} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Data Table Entries */}
            <div className="bg-white border-2 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] flex flex-col h-[550px] overflow-hidden">
              <div className="flex justify-between items-center p-6 border-b-2 border-black shrink-0">
                <div>
                    <h3 className="text-xl font-bold uppercase tracking-wide">Raw Telemetry Readout</h3>
                    <p className="text-[#666] text-sm mt-1">Live environmental feed driving the mathematical engine.</p>
                </div>
                <button onClick={handleDownloadCSV} className="text-xs font-bold uppercase tracking-wider border-2 border-black px-4 py-2 hover:bg-black hover:text-white transition-colors shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
                  Download CSV
                </button>
              </div>

              {/* FWI Parameter Pipeline Diagram */}
              <div className="bg-[#F8F9FA] border-b-2 border-black p-4 flex flex-col md:flex-row gap-4 items-center justify-between text-xs shrink-0">
                 <div className="font-bold uppercase tracking-widest text-black shrink-0">
                    The Physical<br/>Pipeline:
                 </div>
                 <div className="flex-1 flex items-center justify-between gap-2 w-full">
                    <div className="bg-white border-2 border-black p-2 flex-1 text-center shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
                       <span className="font-bold text-[#DC2626]">FFMC</span>
                       <p className="text-[#666] text-[9px] uppercase mt-1 tracking-tight">Surface Dryness</p>
                    </div>
                    <div className="font-bold text-[#888]">→</div>
                    <div className="bg-white border-2 border-black p-2 flex-1 text-center shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
                       <span className="font-bold text-[#DC2626]">DMC</span>
                       <p className="text-[#666] text-[9px] uppercase mt-1 tracking-tight">Mid-Depth Duff</p>
                    </div>
                    <div className="font-bold text-[#888]">→</div>
                    <div className="bg-white border-2 border-black p-2 flex-1 text-center shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
                       <span className="font-bold text-[#DC2626]">DC</span>
                       <p className="text-[#666] text-[9px] uppercase mt-1 tracking-tight">Deep Soil Drought</p>
                    </div>
                    <div className="font-bold text-black text-lg">➔</div>
                    <div className="bg-[#111] text-white border-2 border-black p-2 flex-1 text-center shadow-[2px_2px_0px_0px_rgba(220,38,38,1)]">
                       <span className="font-bold text-white">ISI</span>
                       <p className="text-[#AAA] text-[9px] uppercase mt-1 tracking-tight">Fire Velocity</p>
                    </div>
                 </div>
              </div>

              <div className="flex-1 overflow-auto">
                <table className="w-full text-left text-sm whitespace-nowrap">
                  <thead className="bg-[#F8F9FA] sticky top-0 border-b-2 border-black z-10">
                    <tr>
                      <th className="p-3 border-r-2 border-black align-top w-16">
                        <div className="font-bold text-black">Grid</div>
                        <div className="text-[9px] font-bold text-[#888] uppercase mt-1 leading-tight">Sector<br/>(X,Y)</div>
                      </th>
                      <th className="p-3 border-r-2 border-black align-top">
                        <div className="font-bold text-black">Temp</div>
                        <div className="text-[9px] font-bold text-[#888] uppercase mt-1 leading-tight">Celsius<br/>(°C)</div>
                      </th>
                      <th className="p-3 border-r-2 border-black align-top">
                        <div className="font-bold text-black">RH</div>
                        <div className="text-[9px] font-bold text-[#888] uppercase mt-1 leading-tight">Relative<br/>Humidity (%)</div>
                      </th>
                      <th className="p-3 border-r-2 border-black align-top">
                        <div className="font-bold text-black">Wind</div>
                        <div className="text-[9px] font-bold text-[#888] uppercase mt-1 leading-tight">Speed<br/>(km/h)</div>
                      </th>
                      <th className="p-3 border-r-2 border-black align-top">
                        <div className="font-bold text-[#DC2626]">FFMC</div>
                        <div className="text-[9px] font-bold text-[#888] uppercase mt-1 leading-tight">Fine Fuel Moisture<br/>(Surface Dryness)</div>
                      </th>
                      <th className="p-3 border-r-2 border-black align-top">
                        <div className="font-bold text-[#DC2626]">DMC</div>
                        <div className="text-[9px] font-bold text-[#888] uppercase mt-1 leading-tight">Duff Moisture<br/>(Mid-Depth)</div>
                      </th>
                      <th className="p-3 border-r-2 border-black align-top">
                        <div className="font-bold text-[#DC2626]">DC</div>
                        <div className="text-[9px] font-bold text-[#888] uppercase mt-1 leading-tight">Drought Code<br/>(Deep Soil)</div>
                      </th>
                      <th className="p-3 align-top">
                        <div className="font-bold text-[#DC2626]">ISI</div>
                        <div className="text-[9px] font-bold text-[#888] uppercase mt-1 leading-tight">Initial Spread Index<br/>(Fire Velocity)</div>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.raw_table.map((row: any, i: number) => (
                      <tr key={i} className="border-b border-[#E5E5E5] hover:bg-[#F1F5F9] font-mono text-xs transition-colors">
                        <td className="p-3 border-r-2 border-black/10 font-bold bg-black/5">[{row.X},{row.Y}]</td>
                        <td className="p-3 border-r-2 border-black/10">{row.temp}</td>
                        <td className="p-3 border-r-2 border-black/10">{row.RH}</td>
                        <td className="p-3 border-r-2 border-black/10">{row.wind}</td>
                        <td className="p-3 border-r-2 border-black/10 font-bold text-black">{row.FFMC}</td>
                        <td className="p-3 border-r-2 border-black/10 text-[#555]">{row.DMC}</td>
                        <td className="p-3 border-r-2 border-black/10 text-[#555]">{row.DC}</td>
                        <td className="p-3 text-black font-bold">{row.ISI}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

          </div>

          {/* FINAL ROW: Operational Dispatch Manifest (Full Width) */}
          <div className="bg-white border-2 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] flex flex-col overflow-hidden">
            <div className="flex justify-between items-center p-6 border-b-2 border-black shrink-0 bg-[#111] text-white">
              <div>
                  <h3 className="text-xl font-bold uppercase tracking-wide text-white">Operational Dispatch Manifest</h3>
                  <p className="text-[#AAA] text-sm mt-1">Live GPS disbursal instructions for response teams, sorted by physical fire intensity.</p>
              </div>
              <button 
                onClick={() => {
                  const csv = "data:text/csv;charset=utf-8,Team ID,Latitude,Longitude,Grid X,Grid Y,Intensity Score,Fire Class,Industry Sector\n" 
                    + data.portfolio.map((row: any, i: number) => `TEAM-${String(i+1).padStart(2,'0')},${row.lat},${row.lon},${row.X},${row.Y},${row.ranking_score},${row.fire_type},${row.industry_sector}`).join("\n");
                  const link = document.createElement("a");
                  link.setAttribute("href", encodeURI(csv));
                  link.setAttribute("download", "fire_department_dispatch.csv");
                  document.body.appendChild(link);
                  link.click();
                  document.body.removeChild(link);
                }} 
                className="text-xs font-bold uppercase tracking-wider border-2 border-white px-4 py-2 hover:bg-white hover:text-black transition-colors shadow-[2px_2px_0px_0px_rgba(255,255,255,1)] text-white"
              >
                Export GPS Manifest
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm whitespace-nowrap">
                <thead className="bg-[#F8F9FA] border-b-2 border-black font-bold">
                  <tr>
                    <th className="p-4 border-r-2 border-black uppercase text-[#666] tracking-wider text-xs">Response Unit</th>
                    <th className="p-4 border-r-2 border-black uppercase text-black tracking-wider text-xs">GPS Coordinates</th>
                    <th className="p-4 border-r-2 border-black uppercase text-black tracking-wider text-xs bg-red-50 text-[#DC2626]">NASA FRP (POWER)</th>
                    <th className="p-4 border-r-2 border-black uppercase text-[#666] tracking-wider text-xs">SATELLITE CONFIDENCE</th>
                    <th className="p-4 border-r-2 border-black uppercase text-[#DC2626] tracking-wider text-xs">Intensity (Hazard)</th>
                    <th className="p-4 border-r-2 border-black uppercase text-black tracking-wider text-xs">Fire Classification</th>
                    <th className="p-4 uppercase text-black tracking-wider text-xs">Impacted Industry</th>
                  </tr>
                </thead>
                <tbody>
                  {[...data.portfolio]
                    .sort((a: any, b: any) => b.ranking_score - a.ranking_score)
                    .map((row: any, i: number) => (
                    <tr key={i} className="border-b border-[#E5E5E5] hover:bg-[#F1F5F9] font-mono text-sm transition-colors">
                      <td className="p-4 border-r-2 border-black/10 font-bold bg-black/5 text-black">
                        UNIT-{String(i+1).padStart(2, '0')}
                      </td>
                      <td className="p-4 border-r-2 border-black/10 font-bold text-[#DC2626]">
                        {Number(row.lat || 0).toFixed(5)}, {Number(row.lon || 0).toFixed(5)}
                      </td>
                      <td className="p-4 border-r-2 border-black/10 font-bold bg-red-50 text-[#DC2626]">
                        {row.nasa_frp ? `${Number(row.nasa_frp).toFixed(1)} MW` : 'N/A'}
                      </td>
                      <td className="p-4 border-r-2 border-black/10 font-bold text-xs">
                        {row.nasa_confidence ? (
                          <span className={row.nasa_confidence === 'High' ? 'text-[#DC2626] font-black' : 'text-[#F97316]'}>
                            {row.nasa_confidence.toUpperCase()} ({row.satellite})
                          </span>
                        ) : (
                          <span className="text-[#888]">TERRESTRIAL</span>
                        )}
                      </td>
                      <td className="p-4 border-r-2 border-black/10 font-bold text-black">
                        {Number(row.ranking_score || 0).toFixed(4)}
                      </td>
                      <td className="p-4 border-r-2 border-black/10 font-bold">
                        {row.fire_type}
                      </td>
                      <td className="p-4 font-bold text-[#555]">
                        {row.industry_sector}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      )}
    </div>
  );
}

export default App;
