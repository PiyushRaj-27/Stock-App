
const stockName = JSON.parse(document.getElementById('stock_name').textContent);
let stockData = null;
let chart = null;
let globalCurrency = null;


// utility functions

function showError(message) {
    const popup = document.createElement('div');
    popup.classList.add('popup');
    popup.innerText = message;

    document.body.appendChild(popup);
    setTimeout(() => popup.classList.add('show'), 100); // Small delay for smooth fade-in

    setTimeout(() => {
      popup.classList.remove('show');
      setTimeout(() => popup.remove(), 300); // Allow fade-out before removal
    }, 10000); // 10 seconds
  }

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
            // console.log(data.result);
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
                // console.log(data.result);
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
        appendPrices(stockData.data, stockData.metadata.currency, stockData.metadata.volume);
        renderStockGraph(response.data, stockName);
        closeOrOpen(stockData.metadata.status);
    })
}

get_hourly_stock_data();

function closeOrOpen(status){
    console.log(status);
    if (status === "CLOSED"){
        document.getElementById("closedTag").style.display = "block";
    }
    else{
        document.getElementById("openTag").style.display = "block";
    }
}

// adds DOM element for prices
function appendPrices(data, currency, volume) {
    if(currency){
        globalCurrency = currency;
    }
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

    if(currency){

        closeNumeric.innerText = ` ${currency} ${(lastClose).toFixed(2)}`;
    }
    else{
        closeNumeric.innerText = `${(lastClose).toFixed(2)}`
    }
    // closeNumeric.appendChild(diffIndicator);



    const Low = data.Low;
    const High = data.High;

    const lowest = Math.min(...Object.values(Low));
    const highest = Math.max(...Object.values(High));

    const datas = { "Open": firstOpen, "High": highest, "Low": lowest, "Volume": -1 };
    const datacard = document.getElementById("datacard");
    for (const key in datas) {
        const dataDiv = document.createElement("div");
        dataDiv.classList.add("data");

        const dataKey = document.createElement("div");
        dataKey.classList.add("data-key");

        const dataValue = document.createElement("div");
        dataValue.classList.add(`data-${key}`);
        dataValue.classList.add("data-value");

        dataKey.innerText = key;
        if(key !== 'Volume'){
            dataValue.innerText = `${currency} ${(datas[key]).toFixed(2)}`;
        }
        else{
            dataValue.innerText = (volume).toFixed(2);
        }

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
            gradient = ctx.createLinearGradient(0, 0, 0, 400);
            gradient.addColorStop(0, "rgba(28, 164, 76, 0.5)");
            gradient.addColorStop(0.8, "rgba(28, 164, 76, 0.25)");
            gradient.addColorStop(1, "rgba(28, 164, 76, 0)");
            bcolor = "rgba(28,164,76,1)";
        } else {
            // Red gradient
            gradient = ctx.createLinearGradient(0, 0, 0, 400);
            gradient.addColorStop(0, "rgba(209, 52, 52, 0.5)");
            gradient.addColorStop(0.8, "rgba(209, 52, 52, 0.25)");
            gradient.addColorStop(1, "rgba(209, 52, 52, 0)");
            bcolor = "rgba(209, 52, 52,1)";
        }
    } else {
        // Purple gradient fallback
        gradient = ctx.createLinearGradient(0, 0, 0, 400);
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
    if (!chart || !chart.ctx) {
        console.error("Chart or its rendering context is not available.");
        return;
    }

    const { high, low, sentiment, closingRange } = predictionDataObj || {};

    // Validate new data structure
    if (
        typeof high !== 'number' || typeof low !== 'number' ||
        typeof sentiment !== 'string' || // Added sentiment check
        !closingRange || typeof closingRange.start !== 'number' || typeof closingRange.end !== 'number'
    ) {
        console.error("Prediction data format is invalid:", predictionDataObj);
        return;
    }

    const lastLabelIndex = chart.data.labels.length - 1;
    if (lastLabelIndex < 0) {
        console.error("Chart has no data/labels to base prediction on.");
        return;
    }
    let lastLabel = chart.data.labels[lastLabelIndex];

    // Ensure lastPrice is valid and from the primary dataset (usually the first one)
    const primaryDataset = chart.data.datasets[0];
    if (!primaryDataset || !primaryDataset.data || primaryDataset.data.length === 0) {
        console.error("Primary dataset is missing or empty.");
        return;
    }
    const lastPrice = primaryDataset.data[lastLabelIndex];

    if (typeof lastPrice !== 'number') {
        console.error("Last price from primary dataset is invalid:", lastPrice, "at index", lastLabelIndex);
        return;
    }

    // Date handling for the next prediction point
    let lastLabelDate;
    if (lastLabel instanceof Date) {
        lastLabelDate = lastLabel;
    } else {
        const parsedDate = Date.parse(lastLabel);
        if (isNaN(parsedDate)) {
            console.error("Last label could not be parsed as Date:", lastLabel);
            return;
        }
        lastLabelDate = new Date(parsedDate);
    }

    const nextDayDate = new Date(lastLabelDate);
    nextDayDate.setDate(nextDayDate.getDate() + 1);

    // Color based on sentiment
    let color;
    if (sentiment === 'positive') {
        color = 'rgba(28, 164, 76, 1)'; // Green
    } else if (sentiment === 'negative') {
        color = 'rgba(209, 52, 52, 1)'; // Red
    } else {
        color = 'rgba(255, 205, 86, 1)'; // Yellow for neutral or other
    }

    // Helper function to create data array for a prediction line
    // It connects the last known price to the predicted value
    const createPredictionDataArray = (predictedValue) => {
        const data = Array(chart.data.labels.length + 1).fill(null); // +1 for the new date
        data[lastLabelIndex] = lastPrice; // Point from last actual price
        data[chart.data.labels.length] = predictedValue; // Predicted value at new date index
        return data;
    };

    // --- Create new datasets for the prediction ---

    // High Prediction Line
    const highDataset = {
        label: 'Prediction: High',
        data: createPredictionDataArray(high),
        borderColor: color,
        backgroundColor: 'rgba(0,0,0,0)', // Transparent fill
        pointRadius: 4,
        pointBackgroundColor: color,
        borderWidth: 2,
        fill: false,
        tension: 0 // Straight line
    };

    // Low Prediction Line
    const lowDataset = {
        label: 'Prediction: Low',
        data: createPredictionDataArray(low),
        borderColor: color,
        backgroundColor: 'rgba(0,0,0,0)',
        pointRadius: 4,
        pointBackgroundColor: color,
        borderWidth: 2,
        fill: false,
        tension: 0
    };

    // Closing Range Start Line (dashed)
    const closingStartDataset = {
        label: 'Prediction: Closing Start',
        data: createPredictionDataArray(closingRange.start),
        borderColor: color,
        borderDash: [4, 4], // Dashed line
        backgroundColor: 'rgba(0,0,0,0)',
        pointRadius: 3,
        pointStyle: 'rect', // Different point style
        pointBackgroundColor: color,
        borderWidth: 1.5,
        fill: false,
        tension: 0
    };

    // Closing Range End Line (dashed)
    const closingEndDataset = {
        label: 'Prediction: Closing End',
        data: createPredictionDataArray(closingRange.end),
        borderColor: color,
        borderDash: [4, 4], // Dashed line
        backgroundColor: 'rgba(0,0,0,0)',
        pointRadius: 3,
        pointStyle: 'rect',
        pointBackgroundColor: color,
        borderWidth: 1.5,
        fill: false,
        tension: 0
    };

    // --- Update chart data ---

    // 1. Add the new label (for the next day)
    chart.data.labels.push(nextDayDate);

    // 2. Pad existing datasets with a null for the new label
    // This ensures existing lines don't try to connect to an undefined point
    chart.data.datasets.forEach(dataset => {
        // Only pad if it's shorter than the new labels length
        // This check is important because createPredictionDataArray already made arrays of the new correct length
        if (dataset.data.length < chart.data.labels.length) {
            dataset.data.push(null);
        }
    });

    // 3. Add the new prediction datasets
    chart.data.datasets.push(highDataset, lowDataset, closingStartDataset, closingEndDataset);

    // 4. Update the chart
    chart.update();

    console.log("Prediction added to chart:", predictionDataObj);
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



function addPredictionToDataCard(data){
    const datacard = document.getElementById("datacard");

    Object.keys(data).forEach((key)=>{
        const dataItem = document.createElement("div");
        const dataKey = document.createElement("div");
        const dataVal = document.createElement("div");

        dataItem.classList.add("data");
        dataItem.classList.add("predictedData");
        dataKey.classList.add("data-key");
        dataKey.classList.add(`data-key-${key}`);
        dataVal.classList.add("data-value");
        dataVal.classList.add(`data-val-${key}`);

        dataKey.innerHTML = "Predicted " + key;
        if(key === "closingRange"){

            if(globalCurrency){
                dataVal.innerHTML = `${globalCurrency} ${data[key]["start"]} - ${globalCurrency} ${data[key]["end"]}`;
            }
            else{
                dataVal.innerHTML = `${data[key]["start"]} - ${data[key]["end"]}`;
            }
        }
        else if(key==="sentiment"){
            dataVal.innerHTML = data[key];
        }
        else{
            if(globalCurrency){
                dataVal.innerHTML = `${globalCurrency} ${data[key]}`;
            }
            else{
                dataVal.innerHTML = data[key];
            }
        }
        dataItem.appendChild(dataKey);
        dataItem.appendChild(dataVal);

        datacard.appendChild(dataItem);
    });
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
                console.log(response);
                try {
                    if("success" in response && !response["success"]){
                        showError(response.message);
                    }
                    else{
                        const res = response["result"];
                        // const parsedData = parseStockData(res);
                        console.log(res);
                        addPredictionToChart(res);
                        addPredictionToDataCard(res);
                    }
                } catch (error) {
                    console.error("Error occurred inside getPrediction:", error);
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