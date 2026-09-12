import { useState } from 'react'
import axios from 'axios'
import DeckGL from '@deck.gl/react'
import { HexagonLayer } from '@deck.gl/aggregation-layers'
import Map from 'react-map-gl/maplibre'
import 'maplibre-gl/dist/maplibre-gl.css'
import { BarChart, Bar, XAxis, YAxis, Tooltip as RechartsTooltip, ResponsiveContainer, Scatter, ComposedChart, Line, CartesianGrid, Label } from 'recharts'
import { UploadCloud, Activity, MapPin, Database, TrendingUp, Download } from 'lucide-react'

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
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return
    const file = e.target.files[0]
    const formData = new FormData()
    formData.append('file', file)

    setLoading(true)
    try {
      const res = await axios.post('http://localhost:8000/predict', formData)
      setData(res.data)
    } catch (err) {
      console.error(err)
    }
    setLoading(false)
  }

  const handleDownloadCSV = () => {
    if (!data || !data.portfolio) return;
    const headers = Object.keys(data.portfolio[0]).join(",");
    const rows = data.portfolio.map((row: any) => Object.values(row).join(",")).join("\\n");
    const csv = `${headers}\\n${rows}`;
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'firespec_portfolio.csv';
    a.click();
    window.URL.revokeObjectURL(url);
  }

  const layers: any[] = []

  if (data) {
    layers.push(
      new HexagonLayer({
        id: 'hex',
        data: data.portfolio,
        getPosition: (d: any) => [d.lon, d.lat],
        radius: 400,
        extruded: false, // 2D flat mode as requested
        // Royal Blue to Red/Orange
        colorRange: [
          [2, 48, 71, 150],     // Dark Royal Blue (1)
          [2, 48, 71, 255],     // Solid Royal Blue (2)
          [251, 133, 0, 255],   // Orange (3)
          [208, 0, 0, 255]      // Red (4 - Capacity)
        ],
        pickable: true,
      })
    )
  }

  return (
    <div className="min-h-screen p-6 bg-[#0a0a0a] text-[#e0e0e0] font-sans">
      <header className="mb-10 flex items-center justify-between border-b border-[#222] pb-6">
        <div className="flex items-center gap-4">
          <img src="/logo.png" alt="Firespec Logo" className="invert h-12" />
        </div>
        <label className="cursor-pointer border border-[#FB8500] text-[#FB8500] px-6 py-2 uppercase tracking-widest hover:bg-[#FB8500] hover:text-black transition shadow-[0_0_15px_rgba(251,133,0,0.3)]">
          <UploadCloud className="inline mr-2" /> Upload Telemetry
          <input type="file" className="hidden" onChange={handleFileUpload} />
        </label>
      </header>

      {loading && <div className="text-center text-[#FB8500] animate-pulse text-xl my-20">Initializing Regression Model & Mapping Grid...</div>}

      {data && (
        <div className="flex flex-col gap-8">
          
          {/* Top Row: Analytics & Map */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            
            {/* Left: Regression & Feature Importance */}
            <div className="space-y-8 flex flex-col h-[500px]">
              
              {/* Feature Importance */}
              <div className="bg-[#111] p-6 border border-white/5 shadow-xl flex-1 flex flex-col">
                <h3 className="text-xl font-bold mb-1 flex items-center"><Activity className="mr-2 text-[#FB8500]"/> Feature Importance (XGBoost)</h3>
                <p className="text-gray-400 text-sm mb-4">
                  This chart illustrates the relative contribution (F-Score) of each feature in predicting fire severity. 
                  A higher score means the AI relies more heavily on that specific metric.
                </p>
                <div className="flex-1 min-h-0">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data.feature_importance} layout="vertical" margin={{ left: 20, bottom: 20 }}>
                      <XAxis type="number" stroke="#555" tick={{fill: '#888'}}>
                        <Label value="Relative Importance Score" position="insideBottom" offset={-15} fill="#888" fontSize={12} />
                      </XAxis>
                      <YAxis dataKey="name" type="category" width={80} stroke="#888" tick={{fill: '#888'}} />
                      <RechartsTooltip cursor={{fill: '#222'}} contentStyle={{backgroundColor: '#0a0a0a', border: '1px solid #333'}}/>
                      <Bar dataKey="value" fill="#FB8500" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

            </div>

            {/* Right: H3 Map (Half Size) */}
            <div className="bg-[#111] border border-white/5 shadow-xl relative h-[500px] flex flex-col">
               <div className="absolute top-4 left-4 z-10 bg-black/80 p-4 border border-white/10 pointer-events-none">
                  <h4 className="font-bold text-[#FB8500] mb-2 tracking-wide"><MapPin className="inline w-4 h-4 mr-1"/> H3 2D Global Tracker</h4>
                  <p className="text-sm text-[#023047]">Blue: Stable (1-2)</p>
                  <p className="text-sm text-[#FB8500]">Orange: Elevated (3)</p>
                  <p className="text-sm text-[#D00000] font-bold">Red: Capacity Reached (4)</p>
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
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            
            {/* Regression Plot */}
            <div className="bg-[#111] p-6 border border-white/5 shadow-xl h-[450px] flex flex-col">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-xl font-bold flex items-center"><TrendingUp className="mr-2 text-[#FB8500]"/> Regression Prediction Precision</h3>
                  <p className="text-gray-400 text-sm">Scatter plot with Line of Best Fit showing Prediction Accuracy.</p>
                </div>
                <div className="bg-black/50 border border-[#FB8500]/30 px-4 py-2 text-[#FB8500] font-mono text-sm">
                  {data.regression.equation}
                </div>
              </div>
              <div className="flex-1 min-h-0">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                    <XAxis type="number" dataKey="x" stroke="#888" domain={['dataMin', 'dataMax']}>
                      <Label value={data.regression.xLabel} position="bottom" offset={0} fill="#888" fontSize={12} />
                    </XAxis>
                    <YAxis type="number" dataKey="y" stroke="#888" domain={['dataMin', 'dataMax']}>
                      <Label value={data.regression.yLabel} angle={-90} position="insideLeft" style={{ textAnchor: 'middle' }} fill="#888" fontSize={12} />
                    </YAxis>
                    <RechartsTooltip cursor={{strokeDasharray: '3 3'}} contentStyle={{backgroundColor: '#0a0a0a', border: '1px solid #333'}}/>
                    <Scatter data={data.regression.data} fill="#023047" />
                    <Line data={data.regression.trendline} dataKey="line" stroke="#D00000" strokeWidth={2} dot={false} activeDot={false} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Data Table Entries */}
            <div className="bg-[#111] p-6 border border-white/5 shadow-xl h-[450px] flex flex-col">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-xl font-bold flex items-center"><Database className="mr-2 text-[#FB8500]"/> Raw Telemetry Entries</h3>
                <button onClick={handleDownloadCSV} className="flex items-center text-sm border border-[#FB8500] px-3 py-1 text-[#FB8500] hover:bg-[#FB8500] hover:text-black transition">
                  <Download className="w-4 h-4 mr-2"/> Download Output CSV
                </button>
              </div>
              <div className="flex-1 overflow-auto">
                <table className="w-full text-left text-sm whitespace-nowrap">
                  <thead className="bg-[#222] sticky top-0 text-[#FB8500]">
                    <tr>
                      <th className="p-3">X</th>
                      <th className="p-3">Y</th>
                      <th className="p-3">Month</th>
                      <th className="p-3">Day</th>
                      <th className="p-3">Temp</th>
                      <th className="p-3">Wind</th>
                      <th className="p-3">RH</th>
                      <th className="p-3">Rain</th>
                      <th className="p-3">FFMC</th>
                      <th className="p-3">DMC</th>
                      <th className="p-3">DC</th>
                      <th className="p-3">ISI</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.raw_table.map((row: any, i: number) => (
                      <tr key={i} className="border-b border-[#333] hover:bg-[#1a1a1a]">
                        <td className="p-3">{row.X}</td>
                        <td className="p-3">{row.Y}</td>
                        <td className="p-3 capitalize">{row.month}</td>
                        <td className="p-3 capitalize">{row.day}</td>
                        <td className="p-3">{row.temp}</td>
                        <td className="p-3">{row.wind}</td>
                        <td className="p-3">{row.RH}</td>
                        <td className="p-3">{row.rain}</td>
                        <td className="p-3">{row.FFMC}</td>
                        <td className="p-3">{row.DMC}</td>
                        <td className="p-3">{row.DC}</td>
                        <td className="p-3">{row.ISI}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

          </div>

        </div>
      )}
    </div>
  )
}

export default App
