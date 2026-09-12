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

  const handleFileUpload = async (event: any) => {
    const file = event.target.files[0];
    if (!file) return;

    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post('http://localhost:8000/predict', formData);
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

  const layers: any[] = [];
  if (data) {
    layers.push(
      new HexagonLayer({
        id: 'hex',
        data: data.portfolio,
        getPosition: (d: any) => [d.lon, d.lat],
        radius: 400,
        extruded: false, 
        colorRange: [
          [241, 245, 249, 150],  // Light gray (1)
          [148, 163, 184, 255],  // Solid slate (2)
          [249, 115, 22, 255],   // Orange (3)
          [220, 38, 38, 255]     // Red (4 - Capacity)
        ],
        pickable: true,
      })
    );
  }

  return (
    <div className="w-screen min-h-screen bg-[#F8F9FA] text-[#111111] p-6 lg:p-12 selection:bg-black selection:text-white flex flex-col">
      
      {/* Header */}
      <header className="flex justify-between items-center mb-10 pb-6 border-b-2 border-black shrink-0">
        <div>
          <img src="/firespec-logo.png" alt="FireSpec" className="h-10 object-contain mix-blend-multiply" />
        </div>
        <label className="cursor-pointer border-2 border-black bg-white px-6 py-2 font-bold text-sm tracking-wider uppercase hover:bg-black hover:text-white transition-colors shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
          Upload CSV File
          <input type="file" className="hidden" onChange={handleFileUpload} />
        </label>
      </header>

      {/* Loading State */}
      {loading && (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center text-black font-bold uppercase tracking-widest text-2xl">
            Processing Data...
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
            Upload your environmental data to generate an optimized spatial map and regression analysis.
          </p>
          <label className="cursor-pointer border-4 border-black bg-white px-10 py-5 font-black text-xl tracking-widest uppercase hover:bg-black hover:text-white transition-colors shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]">
            Upload CSV File
            <input type="file" className="hidden" onChange={handleFileUpload} />
          </label>

          <div className="mt-20 grid grid-cols-1 md:grid-cols-3 gap-8 text-left max-w-4xl w-full border-t-2 border-black pt-12">
            <div>
              <h3 className="font-bold text-lg uppercase tracking-wide border-b-2 border-black pb-2 mb-3">1. Format</h3>
              <p className="text-sm font-medium text-[#555]">Ensure your file is formatted with standard environmental metrics.</p>
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
                Relative contribution (F-Score) of each feature in predicting fire severity.
              </p>
              <div className="flex-1 min-h-0">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.feature_importance} layout="vertical" margin={{ left: 20, bottom: 20 }}>
                    <XAxis type="number" stroke="#000" tick={{fill: '#000', fontSize: 12}}>
                      <Label value="Relative Score" position="insideBottom" offset={-15} fill="#000" fontSize={12} fontWeight="bold" />
                    </XAxis>
                    <YAxis dataKey="name" type="category" width={80} stroke="#000" tick={{fill: '#000', fontSize: 12, fontWeight: 'bold'}} />
                    <RechartsTooltip cursor={{fill: '#F1F5F9'}} contentStyle={{backgroundColor: '#FFF', border: '2px solid #000', borderRadius: '0', fontWeight: 'bold'}}/>
                    <Bar dataKey="value" fill="#000" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Right: H3 Map */}
            <div className="bg-white border-2 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] relative h-[500px] flex flex-col">
               <div className="absolute top-0 left-0 z-10 bg-white border-r-2 border-b-2 border-black px-6 py-4 pointer-events-none">
                  <h4 className="font-bold text-black mb-2 uppercase tracking-wide">H3 2D Tracker</h4>
                  <p className="text-sm font-medium text-[#64748B]">Slate: Stable</p>
                  <p className="text-sm font-bold text-[#F97316]">Orange: Elevated</p>
                  <p className="text-sm font-bold text-[#DC2626]">Red: Capacity Reached</p>
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
            <div className="bg-white border-2 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] p-8 h-[500px] flex flex-col">
              <div className="flex justify-between items-start mb-6 border-b-2 border-black pb-4">
                <div>
                  <h3 className="text-xl font-bold uppercase tracking-wide">Prediction Precision</h3>
                  <p className="text-[#666] text-sm mt-1">Variance scatter with Line of Best Fit.</p>
                </div>
                <div className="bg-[#F8F9FA] border-2 border-black px-4 py-2 font-bold font-mono text-sm">
                  {data.regression.equation}
                </div>
              </div>
              <div className="flex-1 min-h-0">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E5E5E5" />
                    <XAxis type="number" dataKey="x" stroke="#000" domain={['dataMin', 'dataMax']}>
                      <Label value={data.regression.xLabel} position="bottom" offset={0} fill="#000" fontSize={12} fontWeight="bold" />
                    </XAxis>
                    <YAxis type="number" dataKey="y" stroke="#000" domain={['dataMin', 'dataMax']}>
                      <Label value={data.regression.yLabel} angle={-90} position="insideLeft" style={{ textAnchor: 'middle' }} fill="#000" fontSize={12} fontWeight="bold" />
                    </YAxis>
                    <RechartsTooltip cursor={{strokeDasharray: '3 3'}} contentStyle={{backgroundColor: '#FFF', border: '2px solid #000', borderRadius: '0', fontWeight: 'bold'}}/>
                    <Scatter data={data.regression.data} fill="#64748B" />
                    <Line data={data.regression.trendline} dataKey="line" stroke="#DC2626" strokeWidth={3} dot={false} activeDot={false} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Data Table Entries */}
            <div className="bg-white border-2 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] flex flex-col h-[500px] overflow-hidden">
              <div className="flex justify-between items-center p-8 border-b-2 border-black shrink-0">
                <h3 className="text-xl font-bold uppercase tracking-wide">Raw Telemetry</h3>
                <button onClick={handleDownloadCSV} className="text-sm font-bold uppercase tracking-wide border-2 border-black px-4 py-2 hover:bg-black hover:text-white transition-colors">
                  Download CSV
                </button>
              </div>
              <div className="flex-1 overflow-auto">
                <table className="w-full text-left text-sm whitespace-nowrap">
                  <thead className="bg-[#F8F9FA] sticky top-0 border-b-2 border-black font-bold">
                    <tr>
                      <th className="p-4 border-r-2 border-black">X</th>
                      <th className="p-4 border-r-2 border-black">Y</th>
                      <th className="p-4 border-r-2 border-black">Month</th>
                      <th className="p-4 border-r-2 border-black">Temp</th>
                      <th className="p-4 border-r-2 border-black">Wind</th>
                      <th className="p-4 border-r-2 border-black">RH</th>
                      <th className="p-4 border-r-2 border-black">Rain</th>
                      <th className="p-4">FFMC</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.raw_table.map((row: any, i: number) => (
                      <tr key={i} className="border-b border-[#E5E5E5] hover:bg-[#F1F5F9] font-mono">
                        <td className="p-4 border-r-2 border-black/10">{row.X}</td>
                        <td className="p-4 border-r-2 border-black/10">{row.Y}</td>
                        <td className="p-4 border-r-2 border-black/10 capitalize">{row.month}</td>
                        <td className="p-4 border-r-2 border-black/10">{row.temp}</td>
                        <td className="p-4 border-r-2 border-black/10">{row.wind}</td>
                        <td className="p-4 border-r-2 border-black/10">{row.RH}</td>
                        <td className="p-4 border-r-2 border-black/10">{row.rain}</td>
                        <td className="p-4">{row.FFMC}</td>
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
  );
}

export default App;
