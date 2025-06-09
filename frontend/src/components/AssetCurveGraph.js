import React from 'react';
import { Line } from 'react-chartjs-2';
import 'chartjs-adapter-date-fns'; // or your preferred date adapter
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale
} from 'chart.js';
import zoomPlugin from 'chartjs-plugin-zoom';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale,
  zoomPlugin
);

const AssetCurveGraph = ({ assetCurveData }) => {
  if (!assetCurveData || assetCurveData.length === 0) {
    return <div>Loading asset curve data...</div>;
  }

  const data = {
    labels: assetCurveData.map(d => d.date),
    datasets: [
      {
        label: 'Equity',
        data: assetCurveData.map(d => d.equity),
        borderColor: 'rgb(75, 192, 192)',
        tension: 0.1,
      },
    ],
  };

  const options = {
    responsive: true,
    scales: {
      x: {
        type: 'time',
        time: {
          unit: 'day' // Adjust time unit as needed
        },
        title: {
          display: true,
          text: 'Date'
        }
      },
      y: {
        title: {
          display: true,
          text: 'Equity'
        }
      }
    },
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: 'Asset Curve',
      },
      zoom: {
        pan: {
          enabled: true,
          mode: 'x',
        },
        zoom: {
          wheel: {
            enabled: true,
          },
          pinch: {
            enabled: true
          },
          mode: 'x',
        }
      }
    }
  };

  return <Line options={options} data={data} />;
};

export default AssetCurveGraph;
