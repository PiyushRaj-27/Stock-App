
const stockName = JSON.parse(document.getElementById('stock_name').textContent);
let stockData = null;
let chart = null;



// optinal websocket code

//const Socket = new WebSocket(
//     'ws://'
//     + window.location.host
//     + '/ws/stock/'
//     + stockName
//     + '/'
// );

// Socket.onmessage = function (e) {
//     const data = JSON.parse(e.data);
//     console.log(data)
//     document.getElementById("socket-data").innerText = `${data.stock} ${data.last_price}`
// };





// utility functions

async function get_hourly_stocks_task_id() {
    try {
        const response = await fetch(`/app/stock/hourly/${stockName}`);
        const result = await response.json();
        return result.task_id;
    }

    catch (error) {
        console.log(`Error in function: get_hourly_stocks_task_id: ${error}`);
        throw new Error("Error!");
    }
}

async function pollResult(taskId, callback) {

    try {
        let call_count = 0;
        const response = await fetch(`/app/infer?task_id=${taskId}`);
        const data = await response.json();

        if (data.status === 'SUCCESS') {
            callback(data.result);
            return;
        }

        else if (data.status === "FAILURE") {
            console.error(`Failed to poll results for task id: ${taskId}`);
            return;
        }

        const interval = setInterval(async () => {
            call_count += 1;
            if (call_count > 5) {
                console.log("Cannot connect to server");
                clearInterval(interval);
            }
            const response = await fetch(`/app/infer?task_id=${taskId}`);
            const data = await response.json();

            if (data.status === 'SUCCESS') {
                clearInterval(interval);
                callback(data.result);
            }
        }, 2000); // poll every 1 second
    }

    catch (error) {
        console.log(`Error in function: pollResult: ${error}`);
        throw new Error("Error");
    }

}



// get the hourly stock data from server, and update the global StockData variable
async function get_hourly_stock_data() {
    const task_id = await get_hourly_stocks_task_id();
    await pollResult(task_id, (response) => {
        stockData = response;
        appendPrices(stockData);
        renderStockGraph(response, stockName);
    })
}

get_hourly_stock_data();

// adds DOM element for prices
function appendPrices(data) {
    data = JSON.parse(data);
    const Close = data.Close;
    const CloseKey = Object.keys(Close);
    const lastCloseKey = CloseKey[CloseKey.length - 1];
    const lastClose = Close[lastCloseKey];

    const Open = data.Open
    const OpenKey = Object.keys(Open);
    const firstOpenKey = OpenKey[0];
    const firstOpen = Open[firstOpenKey];

    const diff = parseFloat(lastClose) - parseFloat(firstOpen);

    const closeNumeric = document.getElementById(`price-${stockName}-close`);
    const diffIndicator = document.createElement("div");
    diffIndicator.classList.add(diff < 0 ? "low-price" : "high-price");
    diffIndicator.innerText = (diff > 0 ? `+ ${(diff).toFixed(2)}` : `- ${(diff).toFixed(2)}`);
    closeNumeric.innerText = (lastClose).toFixed(2);
    // closeNumeric.appendChild(diffIndicator);



    const Low = data.Low;
    const High = data.High;

    const lowest = Math.min(...Object.values(Low));
    const highest = Math.max(...Object.values(High));

    const datas = { "Open": firstOpen, "High": highest, "Low": lowest, "Volume": -1, "MKT CAP": -1, "P/E": -1, "Yield": -1, "Beta": -1 };
    const datacard = document.getElementById("datacard");
    for (const key in datas) {
        const dataDiv = document.createElement("div");
        dataDiv.classList.add("data");

        const dataKey = document.createElement("div");
        dataKey.classList.add("data-key");

        const dataValue = document.createElement("div");
        dataValue.classList.add("data-value");

        dataKey.innerText = key;
        dataValue.innerText = (datas[key]).toFixed(2);

        dataDiv.appendChild(dataKey);
        dataDiv.appendChild(dataValue);
        datacard.appendChild(dataDiv);
    }
}


function renderStockGraph(stockData, stockName) {
    let data = JSON.parse(stockData);
    if (chart) {
        chart.destroy();
    }

    const timestamps = Object.keys(data["Close"]);
    const closePrices = Object.values(data["Close"]);
    const canvasId = `chart-${stockName}`;
    const labels = timestamps.map(ts => new Date(parseInt(ts)));
    const ctx = document.getElementById(canvasId).getContext("2d");

    let gradient;
    let bcolor;

    if (closePrices.length >= 2) {
        const last = closePrices[closePrices.length - 1];
        const first = closePrices[0];

        if (last > first) {
            // Green gradient
            gradient = ctx.createLinearGradient(0, 0, 0, 300);
            gradient.addColorStop(0, "rgba(28, 164, 76, 0.5)");
            gradient.addColorStop(1, "rgba(28, 164, 76, 0)");
            bcolor = "rgba(28,164,76,1)";
        } else {
            // Red gradient
            gradient = ctx.createLinearGradient(0, 0, 0, 300);
            gradient.addColorStop(0, "rgba(209, 52, 52, 0.5)");
            gradient.addColorStop(1, "rgba(209, 52, 52, 0)");
            bcolor = "rgba(209, 52, 52,1)";
        }
    } else {
        // Purple gradient fallback
        gradient = ctx.createLinearGradient(0, 0, 0, 300);
        gradient.addColorStop(0, "rgba(25, 11, 34, 0)");
        gradient.addColorStop(1, "rgba(18, 12, 22, 1)");
        bcolor = "#6a1ed3";
    }

    chart = new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
            datasets: [{
                label: "",
                data: closePrices,
                borderColor: bcolor,
                backgroundColor: gradient,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: "#222",
                    titleColor: "#fff",
                    bodyColor: "#ddd",
                    borderColor: "#6a1ed3",
                    borderWidth: 1,
                },
                zoom: {
                    pan: {
                        enabled: true,
                        mode: 'x',
                        modifierKey: 'ctrl', // or 'alt', 'shift'
                    },
                    zoom: {
                        wheel: {
                            enabled: true,
                            modifierKey: 'ctrl' // safer scroll + zoom
                        },
                        pinch: {
                            enabled: true
                        },
                        mode: 'x',
                    },
                    limits: {
                        x: { min: 'original', max: 'original' },
                        y: { min: 'original', max: 'original' }
                    }
                }
            },
            scales: {
                x: {
                    type: "time",
                    time: {
                        unit: "hour"
                    },
                    ticks: { color: "white" },
                    grid: { display: false }
                },
                y: {
                    ticks: { color: "white" },
                    grid: { display: false },
                }
            }
        },
        plugins: [Chart.registry.getPlugin('zoom')]
    });
}

function renderStockChart(stockData, stockName) {

    const parsedData = JSON.parse(stockData);
    if (chart) {
        chart.destroy()
    }

    const canvasId = `chart-${stockName}`;
    const priceElementId = `price-${stockName}`;
    const timestamps = Object.keys(parsedData["Close"]);
    const ctx = document.getElementById(canvasId).getContext("2d");

    const candleData = timestamps.map(ts => {
        const open = parsedData["Open"][ts];
        const close = parsedData["Close"][ts];
        const isBullish = close >= open;

        return {
            x: parseInt(ts),
            o: open,
            h: parsedData["High"][ts],
            l: parsedData["Low"][ts],
            c: close,
            backgroundColor: isBullish ? getGreenGradient(ctx) : getRedGradient(ctx),
            borderColor: isBullish ? "#1dff4a" : "#ff2222"
        };
    });


    chart = new Chart(ctx, {
        type: "candlestick",
        data: {
            datasets: [{
                label: stockName + " Stock",
                data: candleData,
                borderColor: ctx => ctx.raw.borderColor,
                backgroundColor: ctx => ctx.raw.backgroundColor,
                shadowOffsetX: 2,
                shadowOffsetY: 2,
                shadowBlur: 10,
                shadowColor: "rgba(0, 0, 0, 0.6)",
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: "#1e1b2f",
                    titleColor: "#f6f6f6",
                    bodyColor: "#d2c3ff",
                    borderColor: "#6a1ed3",
                    borderWidth: 1
                }
            },
            scales: {
                x: {
                    type: "time",
                    time: {
                        unit: "hour",
                        tooltipFormat: "ff"
                    },
                    ticks: {
                        color: "#ddd"
                    },
                    grid: { display: false }
                },
                y: {
                    ticks: {
                        color: "#ddd"
                    },
                    grid: { display: false }
                }
            }
        }
    });

    function getGreenGradient(ctx) {
        const gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, "#1dff4a");
        gradient.addColorStop(1, "#1dff4a");
        return gradient;
    }

    function getRedGradient(ctx) {
        const gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, "#ff2222");
        gradient.addColorStop(1, "#ff2222");
        return gradient;
    }

}


function addPredictionToChart(predictionDataObj) {

    if (!chart) {
        console.error("Chart object is not available. Cannot add prediction.");
        return;
    }
    const ctx = chart.ctx;
    if (!ctx) {
        console.error("Could not get rendering context (chart.ctx). Cannot create gradient.");
        return;
    }
    if (!chart.data || !chart.data.labels || !chart.data.datasets || chart.data.datasets.length === 0 || chart.data.labels.length === 0) {
        console.error("Chart data structure seems incomplete or empty. Cannot add prediction.");
        return;
    }
    if (chart.data.datasets[0].data.length !== chart.data.labels.length) {
        console.error("Chart labels and data points count mismatch. Cannot reliably add prediction.");
        return;
    }

    const predictionResult = predictionDataObj;

    if (!predictionResult || typeof predictionResult.data !== 'string' || predictionResult.success !== 'True') {
        console.error(`Prediction data object format invalid or success is not 'True'. Received:`, predictionResult);
        return;
    }

    const predictedPrice = parseFloat(predictionResult.data);
    if (isNaN(predictedPrice)) {
        console.error(`Predicted price is not a valid number: '${predictionResult.data}'`);
        return;
    }
    const lastLabelIndex = chart.data.labels.length - 1;
    let lastLabel = chart.data.labels[lastLabelIndex];
    const lastPrice = chart.data.datasets[0].data[lastLabelIndex];

    if (typeof lastPrice !== 'number' || isNaN(lastPrice)) {
        console.error(`Last historical price is not a valid number: '${lastPrice}'. Cannot determine prediction color/gradient.`);
        return;
    }

    if (!(lastLabel instanceof Date)) {
        console.warn("The last label in the chart is not a Date object. Attempting to parse.", "Label:", lastLabel);
        const timestamp = Date.parse(lastLabel);
        if (isNaN(timestamp)) {
            console.error("Could not interpret the last label as a valid date/time.");
            return;
        }
        lastLabel = new Date(timestamp);
    }

    const nextDayDate = new Date(lastLabel);
    nextDayDate.setDate(nextDayDate.getDate() + 1);

    let predictionLineColor;
    let predictionPointColor;
    let predictionGradient;

    predictionGradient = ctx.createLinearGradient(0, 0, 0, 300);

    if (predictedPrice > lastPrice) {
        predictionLineColor = 'rgba(28, 164, 76, 1)';
        predictionPointColor = 'rgba(28, 164, 76, 1)';

        predictionGradient.addColorStop(0, "rgba(28, 164, 76, 0.5)"); 
        predictionGradient.addColorStop(1, "rgba(28, 164, 76, 0)");   
    } else if (predictedPrice < lastPrice) {

        predictionLineColor = 'rgba(209, 52, 52, 1)';
        predictionPointColor = 'rgba(209, 52, 52, 1)';

        predictionGradient.addColorStop(0, "rgba(209, 52, 52, 0.5)"); 
        predictionGradient.addColorStop(1, "rgba(209, 52, 52, 0)");   
    } else {

        predictionLineColor = 'rgb(255, 205, 86)';
        predictionPointColor = 'rgb(255, 205, 86)';
        predictionGradient.addColorStop(0, "rgba(255, 205, 86, 0.5)"); 
        predictionGradient.addColorStop(1, "rgba(255, 205, 86, 0)");  
    }


    const predictionDataset = {
        label: 'Prediction',
        data: [],
        borderColor: predictionLineColor,
        pointBackgroundColor: predictionPointColor,
        pointBorderColor: 'white',
        fill: true,                      
        backgroundColor: predictionGradient,

        borderWidth: 2,
        borderDash: [5, 5],
        pointRadius: 5,
        pointHoverRadius: 7,
        tension: 0.1 
    };

    predictionDataset.data = chart.data.labels.map(() => null);
    predictionDataset.data[lastLabelIndex] = lastPrice;
    predictionDataset.data.push(predictedPrice);


    chart.data.labels.push(nextDayDate);
    chart.data.datasets.push(predictionDataset);

    chart.update();

}


async function getPredictionToken() {

    try{
        let predictionTokenJson = await fetch(`/app/stock/prediction/${stockName}`);
        let predictionTokenRes = await predictionTokenJson.json();
        return predictionTokenRes.task_id;
    }
    catch (error){
        console.log(`Error in function: getPredictionToken: ${error}`);
        throw new Error("Error");
    }

}

async function getPrediction() {
    let token;
    try {
        token = await getPredictionToken();
    } catch (error) {
        console.error("Error occurred while getting prediction token:", error);
        return;
    }


    if (token) {
        await pollResult(token,
            (response) => { // Success Callback for pollResult
                try {
                    addPredictionToChart(response);
                } catch (error) {
                    console.error("Error occurred inside addPredictionToChart:", error);
                }
            },
            (error) => {
                console.error("Polling failed for prediction task:", error);
            }
        );
    } else {
        console.error("Could not get prediction token. Prediction fetch aborted.");
    }
}